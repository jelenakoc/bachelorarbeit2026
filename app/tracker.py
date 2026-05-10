import ctypes
import time
from ctypes import wintypes
from datetime import datetime
import win32gui
import win32process
import psutil
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine
from app.models import Base, ActivityLog, ProjectKeyword, ProjectTask
from app.paths import APP_ROOT
from app.popup import ask_project_for_block

Base.metadata.create_all(bind=engine)

IDLE_STOP_SECONDS = 300
MIN_ACTIVITY_SECONDS = 60
POLL_INTERVAL_SECONDS = 2
TRACKING_STATE_FILE = APP_ROOT / "tracking_state.txt"

#Aktives-Fenstertitel
def get_active_window_title():
    window = win32gui.GetForegroundWindow()
    return win32gui.GetWindowText(window)

#Aktives-Fenster-App-Name
def get_active_app_name():
    try:
        window = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(window)
        process = psutil.Process(pid)
        return process.name()
    except Exception:
        return None

#Inaktvität
def get_idle_seconds() -> float:
    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.UINT),
            ("dwTime", wintypes.DWORD),
        ]

    last_input_info = LASTINPUTINFO()
    last_input_info.cbSize = ctypes.sizeof(LASTINPUTINFO)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(last_input_info))

    milliseconds = ctypes.windll.kernel32.GetTickCount() - last_input_info.dwTime
    return milliseconds / 1000.0

#Bei Inaktivität Popup anzeigen
def show_idle_pause_popup():
    ctypes.windll.user32.MessageBoxW(
        0,
        "Sie waren 5 Minuten inaktiv. Die Zeiterfassung ist jetzt pausiert.",
        "Tracking pausiert",
        0x40
    )

#Tracking-Status aus gemeinsamer Datei lesen
def is_tracking_enabled() -> bool:
    try:
        return TRACKING_STATE_FILE.read_text(encoding="utf-8").strip() != "0"
    except FileNotFoundError:
        return True
    except OSError:
        return True


#Projekt-Match anhand von Keywords im Fenstertitel finden
def find_project_match(db: Session, window_title: str, block_date):
    if not window_title:
        return None, None

    title_lower = window_title.lower()
    keywords = db.query(ProjectKeyword).all()

    for keyword_entry in keywords:
        project = keyword_entry.project
        keyword_lower = keyword_entry.keyword.lower()

        if not project:
            continue

        if not project.is_active:
            continue

        if project.active_from and block_date < project.active_from:
            continue

        if project.active_to and block_date > project.active_to:
            continue

        if keyword_lower in title_lower:
            return keyword_entry.project_id, keyword_entry.keyword

    return None, None


#Vergleich, ob Kontext gleich bleibt oder neuer Block beginnt
def is_same_context(
    last_app: str | None,
    current_app: str | None,
    last_title: str | None,
    current_title: str | None,
    db: Session,
    block_date,
):
    if last_app != current_app:
        return False

    last_project_id, _ = find_project_match(db, last_title or "", block_date)
    current_project_id, _ = find_project_match(db, current_title or "", block_date)

    if last_project_id is not None and current_project_id is not None:
        return last_project_id == current_project_id

    return True


#Wenn Nutzer manuell Projekt/Aufgabe zuordnet, neue Aufgabe speichern, falls sie noch nicht existiert
def save_task_if_new(db: Session, project_id: int | None, task_text: str):
    if not project_id or not task_text:
        return

    existing = db.query(ProjectTask).filter(
        ProjectTask.project_id == project_id,
        ProjectTask.name == task_text
    ).first()

    if not existing:
        new_task = ProjectTask(
            project_id=project_id,
            name=task_text
        )
        db.add(new_task)
        db.commit()

#Aktivitätsblock speichern
def save_activity_block(
    db: Session,
    app_name: str,
    window_title: str | None,
    matched_keyword: str | None,
    project_id: int | None,
    task_text: str,
    comment_text: str,
    needs_review: bool,
    start_time: datetime,
    end_time: datetime,
):
    duration = (end_time - start_time).total_seconds()

    if duration < MIN_ACTIVITY_SECONDS:
        print(f"Block ignoriert, weil kürzer als {MIN_ACTIVITY_SECONDS} Sekunden.")
        return
    
    
    save_task_if_new(db, project_id, task_text)

    activity = ActivityLog(
        app_name=app_name,
        window_title=window_title,
        start_time=start_time,
        end_time=end_time,
        duration_seconds=duration,
        matched_keyword=matched_keyword,
        project_id=project_id,
        task_text=task_text,
        comment_text=comment_text,
        needs_review=needs_review
    )

    db.add(activity)
    db.commit()

    if project_id:
        print(f"Block gespeichert mit Projekt-Match: {matched_keyword or 'manuell'}")
    else:
        print("Block gespeichert ohne Projekt-Match")

#Wenn kein Projekt erkannt wurde, aber Block lang genug ist, Nutzer fragen
def maybe_ask_user_for_project(db: Session, app_name: str, duration: float, project_id: int | None):
    if duration < MIN_ACTIVITY_SECONDS:
        return None, None, "", "", True

    popup_result = ask_project_for_block(app_name, suggested_project_id=project_id)

    if popup_result["action"] == "assign":
        return (
            popup_result["project_id"],
            "manuell" if popup_result["project_id"] != project_id else None,
            popup_result.get("task_text", ""),
            popup_result.get("comment_text", ""),
            False
        )

    return (
        None,
        None,
        popup_result.get("task_text", ""),
        popup_result.get("comment_text", ""),
        True
    )

#Block finalisieren: Projekt-Match finden, ggf. Nutzer fragen, Block speichern
def finalize_current_block(
    db: Session,
    last_app: str | None,
    last_title: str | None,
    block_start: datetime,
    end_time: datetime,
    allow_popup: bool,
):
    duration = (end_time - block_start).total_seconds()
    project_id, matched_keyword = find_project_match(db, last_title or "", block_start.date())

    if allow_popup:
        project_id, manual_marker, task_text, comment_text, needs_review = maybe_ask_user_for_project(
            db=db,
            app_name=last_app or "Unbekannt",
            duration=duration,
            project_id=project_id
        )

        if manual_marker == "manuell":
            matched_keyword = "manuell"
    else:
        task_text = ""
        comment_text = ""
        needs_review = project_id is None

    save_activity_block(
        db=db,
        app_name=last_app or "Unbekannt",
        window_title=last_title,
        matched_keyword=matched_keyword,
        project_id=project_id,
        task_text=task_text,
        comment_text=comment_text,
        needs_review=needs_review,
        start_time=block_start,
        end_time=end_time
    )

    return duration

#Hauptschleife: Aktives Fenster überwachen, Blöcke finalisieren, bei Inaktivität pausieren und Popup anzeigen
def main():
    print("Tracker gestartet. DrÃ¼cke STRG+C zum Beenden.")

    db = SessionLocal()

    last_title = get_active_window_title()
    last_app = get_active_app_name()
    block_start = datetime.now()
    tracking_paused_for_idle = False
    tracking_paused_for_manual_stop = False

    print(f"Neuer Block in App: {last_app}")

    try:
        while True:
            if not is_tracking_enabled():
                if not tracking_paused_for_manual_stop:
                    now = datetime.now()
                    finalize_current_block(
                        db=db,
                        last_app=last_app,
                        last_title=last_title,
                        block_start=block_start,
                        end_time=now,
                        allow_popup=False,
                    )
                    tracking_paused_for_manual_stop = True
                    print("Tracking manuell pausiert.")

                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            if tracking_paused_for_manual_stop:
                last_title = get_active_window_title()
                last_app = get_active_app_name()
                block_start = datetime.now()
                tracking_paused_for_manual_stop = False
                print(f"Tracking fortgesetzt in App: {last_app}")

            idle_seconds = get_idle_seconds()

            if idle_seconds >= IDLE_STOP_SECONDS:
                if not tracking_paused_for_idle:
                    now = datetime.now()
                    duration = finalize_current_block(
                        db=db,
                        last_app=last_app,
                        last_title=last_title,
                        block_start=block_start,
                        end_time=now,
                        allow_popup=False
                    )
                    tracking_paused_for_idle = True
                    show_idle_pause_popup()
                    print(f"Tracking pausiert wegen InaktivitÃ¤t nach {duration:.2f} Sekunden.")

                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            if tracking_paused_for_idle:
                last_title = get_active_window_title()
                last_app = get_active_app_name()
                block_start = datetime.now()
                tracking_paused_for_idle = False
                print(f"Tracking fortgesetzt in App: {last_app}")

            current_title = get_active_window_title()
            current_app = get_active_app_name()

            same_context = is_same_context(
                last_app=last_app,
                current_app=current_app,
                last_title=last_title,
                current_title=current_title,
                db=db,
                block_date=block_start.date()
            )

            if not same_context:
                now = datetime.now()
                duration = finalize_current_block(
                    db=db,
                    last_app=last_app,
                    last_title=last_title,
                    block_start=block_start,
                    end_time=now,
                    allow_popup=True
                )

                print(f"Block beendet in App: {last_app} | Dauer: {duration:.2f} Sekunden")

                last_title = current_title
                last_app = current_app
                block_start = now

                print(f"Neuer Block in App: {current_app}")
            else:
                last_title = current_title
                last_app = current_app

            time.sleep(POLL_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        now = datetime.now()
        duration = 0

        if not tracking_paused_for_idle:
            duration = finalize_current_block(
                db=db,
                last_app=last_app,
                last_title=last_title,
                block_start=block_start,
                end_time=now,
                allow_popup=True
            )

        print(f"\nLetzter Block beendet in App: {last_app} | Dauer: {duration:.2f} Sekunden")
        print("Tracker beendet.")

    finally:
        db.close()


if __name__ == "__main__":
    main()

