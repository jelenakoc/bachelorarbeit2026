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
from app.popup import ask_project_for_block

Base.metadata.create_all(bind=engine)

IDLE_STOP_SECONDS = 300
MIN_ACTIVITY_SECONDS = 60
POLL_INTERVAL_SECONDS = 2


def get_active_window_title():
    window = win32gui.GetForegroundWindow()
    return win32gui.GetWindowText(window)


def get_active_app_name():
    try:
        window = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(window)
        process = psutil.Process(pid)
        return process.name()
    except Exception:
        return None


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


def show_idle_pause_popup():
    ctypes.windll.user32.MessageBoxW(
        0,
        "Sie waren 5 Minuten inaktiv. Die Zeiterfassung ist jetzt pausiert.",
        "Tracking pausiert",
        0x40
    )


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

def is_same_context(
    last_app: str | None,
    current_app: str | None,
    last_title: str | None,
    current_title: str | None,
    db: Session,
    block_date
):
    # Wenn die App wechselt -> neuer Block
    if last_app != current_app:
        return False

    # Projekt-Match fÃ¼r beide Titel prÃ¼fen
    last_project_id, _ = find_project_match(db, last_title or "", block_date)
    current_project_id, _ = find_project_match(db, current_title or "", block_date)

    # Wenn beide Titel demselben Projekt zugeordnet werden kÃ¶nnen:
    # gleicher Kontext
    if last_project_id is not None and current_project_id is not None:
        return last_project_id == current_project_id

    # Wenn kein Projekt erkannt wird, aber die App gleich bleibt:
    # erstmal als gleicher Block behandeln
    return True

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


def maybe_ask_user_for_project(db: Session, app_name: str, duration: float, project_id: int | None):
    if project_id is not None:
        return project_id, None, "", "", False

    if duration < MIN_ACTIVITY_SECONDS:
        return None, None, "", "", True

    popup_result = ask_project_for_block(app_name)

    if popup_result["action"] == "assign":
        return (
            popup_result["project_id"],
            "manuell",
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


def main():
    print("Tracker gestartet. DrÃ¼cke STRG+C zum Beenden.")

    db = SessionLocal()

    last_title = get_active_window_title()
    last_app = get_active_app_name()
    block_start = datetime.now()
    tracking_paused_for_idle = False

    print(f"Neuer Block in App: {last_app}")

    try:
        while True:
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
                # gleicher Kontext: Titel kann sich Ã¤ndern, aber Block bleibt bestehen
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

