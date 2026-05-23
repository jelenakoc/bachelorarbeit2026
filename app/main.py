import csv
import io
import math
import atexit
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine
from app.models import Base, Project, ActivityLog, ProjectKeyword, ProjectTask
from app.paths import APP_ROOT, get_resource_path
from app.schemas import ProjectCreate

#Api-Anwendung
app = FastAPI(title="BA Zeiterfassung API")

Base.metadata.create_all(bind=engine)

TRACKING_STATE_FILE = APP_ROOT / "tracking_state.txt"
tracker_process: subprocess.Popen | None = None


def is_tracking_enabled() -> bool:
    try:
        return TRACKING_STATE_FILE.read_text(encoding="utf-8").strip() != "0"
    except FileNotFoundError:
        return False
    except OSError:
        return False


def set_tracking_enabled(enabled: bool) -> bool:
    TRACKING_STATE_FILE.write_text("1" if enabled else "0", encoding="utf-8")
    return enabled


def get_tracker_command() -> list[str] | None:
    if getattr(sys, "frozen", False):
        tracker_exe = APP_ROOT / "Tracker" / "Tracker.exe"
        if tracker_exe.exists():
            return [str(tracker_exe)]
        return None

    tracker_script = Path(__file__).resolve().parent / "tracker.py"
    return [sys.executable, str(tracker_script)]


def is_started_tracker_running() -> bool:
    return tracker_process is not None and tracker_process.poll() is None


def start_tracker_process() -> bool:
    global tracker_process

    if is_started_tracker_running():
        return True

    command = get_tracker_command()
    if command is None:
        return False

    creationflags = 0
    startupinfo = None

    if sys.platform == "win32":
        creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)

    tracker_process = subprocess.Popen(
        command,
        cwd=str(APP_ROOT),
        creationflags=creationflags,
        startupinfo=startupinfo,
    )
    return True


def stop_started_tracker_process():
    global tracker_process

    if not is_started_tracker_running():
        tracker_process = None
        return

    tracker_process.terminate()
    try:
        tracker_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        tracker_process.kill()
    finally:
        tracker_process = None


def shutdown_tracker_process():
    stop_started_tracker_process()


atexit.register(shutdown_tracker_process)


@app.on_event("startup")
def reset_tracking_on_dashboard_start():
    set_tracking_enabled(False)

#Aufrunden auf 15 Minuten
def round_to_15_minutes(seconds: float) -> float:
    if seconds <= 0:
        return 0

    minutes = seconds / 60
    rounded_minutes = math.ceil(minutes / 15) * 15
    return rounded_minutes * 60

#Zeitblock in lesbarer Form bringen
def format_hours_and_minutes(decimal_hours: float) -> str:
    total_minutes = round(decimal_hours * 60)
    hours = total_minutes // 60
    minutes = total_minutes % 60

    if hours and minutes:
        return f"{hours} Std {minutes} Min"
    if hours:
        return f"{hours} Std"
    return f"{minutes} Min"

#Dezimalzahlen für CSV mit Komma formatieren
def format_decimal_for_csv(value: float | int) -> str:
    return f"{value:.2f}".replace(".", ",")

#Stats als CSV exportieren
def build_task_stats_csv(task_stats: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(["Projekt", "Aufgabe", "Gemessen", "Abrechenbar", "Stundensatz (€)", "Umsatz (€)"])

    for item in task_stats:
        writer.writerow(
            [
                item["project_name"],
                item["task_name"],
                format_decimal_for_csv(item["total_hours_raw"]),
                format_decimal_for_csv(item["total_hours_billable"]),
                format_decimal_for_csv(item["hourly_rate"]),
                format_decimal_for_csv(item["revenue"]),
            ]
        )

    return "\ufeff" + buffer.getvalue()

#Datenmodelle für API-Requests
class ActivityUpdate(BaseModel):
    project_id: int | None = None
    task_text: str = ""
    comment_text: str = ""
    needs_review: bool = False
    start_time: datetime | None = None
    end_time: datetime | None = None


class TrackingSetRequest(BaseModel):
    enabled: bool


class ProjectUpdate(BaseModel):
    name: str
    color: str | None = None
    hourly_rate: float | None = None
    active_from: date | None = None
    active_to: date | None = None
    is_active: bool = True
    keywords: list[str] = Field(default_factory=list)

#Hilfsfunktion, um Zeiträume für Statistiken zu berechnen
def get_period_range(
    period: str,
    selected_date: str | None = None,
    selected_month: str | None = None,
    selected_year: str | None = None,
    selected_quarter: str | None = None,
):
    if period == "day":
        if selected_date:
            start = datetime.strptime(selected_date, "%Y-%m-%d")
        else:
            now = datetime.now()
            start = datetime(now.year, now.month, now.day)
        end = start + timedelta(days=1)

    elif period == "week":
        if selected_date:
            ref = datetime.strptime(selected_date, "%Y-%m-%d")
        else:
            now = datetime.now()
            ref = datetime(now.year, now.month, now.day)

        start = ref - timedelta(days=ref.weekday())
        end = start + timedelta(days=7)

    elif period == "month":
        if selected_month:
            start = datetime.strptime(selected_month + "-01", "%Y-%m-%d")
        else:
            now = datetime.now()
            start = datetime(now.year, now.month, 1)

        if start.month == 12:
            end = datetime(start.year + 1, 1, 1)
        else:
            end = datetime(start.year, start.month + 1, 1)

    elif period == "quarter":
        now = datetime.now()

        if selected_quarter:
            year_str, quarter_str = selected_quarter.split("-Q")
            year = int(year_str)
            quarter = int(quarter_str)
        else:
            year = now.year
            quarter = ((now.month - 1) // 3) + 1

        start_month = (quarter - 1) * 3 + 1
        start = datetime(year, start_month, 1)

        if quarter == 4:
            end = datetime(year + 1, 1, 1)
        else:
            end = datetime(year, start_month + 3, 1)

    elif period == "year":
        now = datetime.now()

        if selected_year:
            year = int(selected_year)
        else:
            year = now.year

        start = datetime(year, 1, 1)
        end = datetime(year + 1, 1, 1)

    else:
        now = datetime.now()
        start = datetime(now.year, now.month, 1)

        if now.month == 12:
            end = datetime(now.year + 1, 1, 1)
        else:
            end = datetime(now.year, now.month + 1, 1)

    return start, end

#Api direkt aufrufen:
@app.get("/")
def root():
    return {"message": "API läuft"}


@app.get("/tracking/status")
def get_tracking_status():
    enabled = is_tracking_enabled()
    return {
        "enabled": enabled,
        "process_running": is_started_tracker_running(),
    }


@app.post("/tracking/toggle")
def toggle_tracking():
    enabled = set_tracking_enabled(not is_tracking_enabled())
    if enabled and not start_tracker_process():
        set_tracking_enabled(False)
        raise HTTPException(status_code=500, detail="Tracker konnte nicht gestartet werden.")

    return {
        "enabled": enabled,
        "process_running": is_started_tracker_running(),
    }


@app.post("/tracking/set")
def set_tracking_state(request: TrackingSetRequest):
    enabled = set_tracking_enabled(request.enabled)
    if enabled and not start_tracker_process():
        set_tracking_enabled(False)
        raise HTTPException(status_code=500, detail="Tracker konnte nicht gestartet werden.")

    return {
        "enabled": enabled,
        "process_running": is_started_tracker_running(),
    }

#Projekte abrufen
@app.get("/projects")
def get_projects():
    db: Session = SessionLocal()
    try:
        projects = db.query(Project).all()
        return [
            {
                "id": project.id,
                "name": project.name,
                "color": project.color,
                "hourly_rate": project.hourly_rate,
                "active_from": project.active_from,
                "active_to": project.active_to,
                "is_active": project.is_active,
                "keywords": [keyword.keyword for keyword in project.keywords],
            }
            for project in projects
        ]
    finally:
        db.close()

#Projekt anlegen
@app.post("/projects")
def create_project(project_data: ProjectCreate):
    db: Session = SessionLocal()
    try:
        existing_project = db.query(Project).filter(Project.name == project_data.name).first()
        if existing_project:
            raise HTTPException(status_code=400, detail="Projektname existiert bereits.")

        project = Project(
            name=project_data.name,
            color=project_data.color,
            hourly_rate=project_data.hourly_rate,
            active_from=project_data.active_from,
            active_to=project_data.active_to,
            is_active=True,
        )

        for keyword in project_data.keywords:
            project.keywords.append(ProjectKeyword(keyword=keyword))

        db.add(project)
        db.commit()
        db.refresh(project)
        return {"message": "Projekt erstellt", "project_id": project.id}
    finally:
        db.close()

#Bestehendes Projekt ändern
@app.patch("/projects/{project_id}")
def update_project(project_id: int, project_data: ProjectUpdate):
    db: Session = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Projekt nicht gefunden.")

        duplicate = (
            db.query(Project)
            .filter(Project.name == project_data.name)
            .filter(Project.id != project_id)
            .first()
        )
        if duplicate:
            raise HTTPException(status_code=400, detail="Projektname existiert bereits.")

        project.name = project_data.name
        project.color = project_data.color
        project.hourly_rate = project_data.hourly_rate
        project.active_from = project_data.active_from
        project.active_to = project_data.active_to
        project.is_active = project_data.is_active

        db.query(ProjectKeyword).filter(ProjectKeyword.project_id == project_id).delete()
        for keyword in project_data.keywords:
            cleaned_keyword = keyword.strip()
            if cleaned_keyword:
                db.add(ProjectKeyword(keyword=cleaned_keyword, project_id=project_id))

        db.commit()
        return {"message": "Projekt aktualisiert", "project_id": project.id}
    finally:
        db.close()

#Projekte deaktivieren (nicht löschen)
@app.patch("/projects/{project_id}/deactivate")
def deactivate_project(project_id: int, active_to: date | None = None):
    db: Session = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Projekt nicht gefunden.")

        project.is_active = False
        project.active_to = active_to if active_to else date.today()
        db.commit()
        return {
            "message": "Projekt deaktiviert",
            "project_id": project.id,
            "active_to": project.active_to,
        }
    finally:
        db.close()

#Aufgaben für Projekt abrufen
@app.get("/projects/{project_id}/tasks")
def get_tasks_for_project(project_id: int):
    db: Session = SessionLocal()
    try:
        tasks = db.query(ProjectTask).filter(ProjectTask.project_id == project_id).all()
        return [{"id": task.id, "name": task.name} for task in tasks]
    finally:
        db.close()

#Aufgabe für Projekt löschen
@app.delete("/projects/{project_id}/tasks/{task_id}")
def delete_task_for_project(project_id: int, task_id: int):
    db: Session = SessionLocal()
    try:
        task = (
            db.query(ProjectTask)
            .filter(ProjectTask.id == task_id, ProjectTask.project_id == project_id)
            .first()
        )
        if not task:
            raise HTTPException(status_code=404, detail="Aufgabe nicht gefunden.")

        db.delete(task)
        db.commit()
        return {"message": "Aufgabe gelöscht", "task_id": task_id}
    finally:
        db.close()

#Zeitblöcke abrufen
@app.get("/activities")
def get_activities():
    db: Session = SessionLocal()
    try:
        activities = db.query(ActivityLog).order_by(ActivityLog.start_time.desc()).all()
        return [
            {
                "id": activity.id,
                "app_name": activity.app_name,
                "window_title": activity.window_title,
                "start_time": activity.start_time,
                "end_time": activity.end_time,
                "duration_seconds": activity.duration_seconds,
                "matched_keyword": activity.matched_keyword,
                "project_id": activity.project_id,
                "project_name": activity.project.name if activity.project else None,
                "task_text": activity.task_text,
                "needs_review": activity.needs_review,
                "comment_text": activity.comment_text,
            }
            for activity in activities
        ]
    finally:
        db.close()

#Aktivität aktualisieren
@app.patch("/activities/{activity_id}")
def update_activity(activity_id: int, update_data: ActivityUpdate):
    db: Session = SessionLocal()
    try:
        activity = db.query(ActivityLog).filter(ActivityLog.id == activity_id).first()
        if not activity:
            raise HTTPException(status_code=404, detail="Aktivität nicht gefunden.")

        cleaned_task_text = update_data.task_text.strip()
        cleaned_comment_text = update_data.comment_text.strip()
        new_start_time = update_data.start_time or activity.start_time
        new_end_time = update_data.end_time or activity.end_time

        if new_end_time <= new_start_time:
            raise HTTPException(
                status_code=400,
                detail="Endzeit muss nach der Startzeit liegen.",
            )

        if update_data.needs_review is False and update_data.project_id is None:
            raise HTTPException(
                status_code=400,
                detail="Ein offener Zeitblock kann nicht ohne Projekt gespeichert werden.",
            )

        if (
            update_data.needs_review is False
            and not cleaned_task_text
            and not cleaned_comment_text
        ):
            raise HTTPException(
                status_code=400,
                detail="Ein offener Zeitblock braucht mindestens Aufgabe oder Kommentar.",
            )

        activity.project_id = update_data.project_id
        activity.task_text = cleaned_task_text
        activity.comment_text = cleaned_comment_text
        activity.needs_review = update_data.needs_review
        activity.start_time = new_start_time
        activity.end_time = new_end_time
        activity.duration_seconds = int((new_end_time - new_start_time).total_seconds())

        if update_data.project_id and cleaned_task_text:
            existing = db.query(ProjectTask).filter(
                ProjectTask.project_id == update_data.project_id,
                ProjectTask.name == cleaned_task_text,
            ).first()
            if not existing:
                db.add(ProjectTask(project_id=update_data.project_id, name=cleaned_task_text))

        db.commit()
        return {"message": "Aktivität aktualisiert"}
    finally:
        db.close()

#Zeitblock löschen
@app.delete("/activities/{activity_id}")
def delete_activity(activity_id: int):
    db: Session = SessionLocal()
    try:
        activity = db.query(ActivityLog).filter(ActivityLog.id == activity_id).first()
        if not activity:
            raise HTTPException(status_code=404, detail="Aktivität nicht gefunden.")

        db.delete(activity)
        db.commit()
        return {"message": "Aktivität gelöscht"}
    finally:
        db.close()

#Zeitblöcke für Projekt abrufen
@app.get("/activities/by-project/{project_id}")
def get_activities_by_project(
    project_id: int,
    period: str = Query(default="month"),
    selected_date: str | None = None,
    selected_month: str | None = None,
    selected_year: str | None = None,
    selected_quarter: str | None = None,
):
    db: Session = SessionLocal()
    try:
        start, end = get_period_range(period, selected_date, selected_month, selected_year, selected_quarter)
        activities = (
            db.query(ActivityLog)
            .filter(ActivityLog.project_id == project_id)
            .filter(ActivityLog.start_time >= start)
            .filter(ActivityLog.start_time < end)
            .order_by(ActivityLog.start_time.desc())
            .all()
        )

        return [
            {
                "id": activity.id,
                "app_name": activity.app_name,
                "window_title": activity.window_title,
                "start_time": activity.start_time,
                "end_time": activity.end_time,
                "duration_seconds": activity.duration_seconds,
                "matched_keyword": activity.matched_keyword,
                "project_id": activity.project_id,
                "task_text": activity.task_text,
                "needs_review": activity.needs_review,
                "comment_text": activity.comment_text,
            }
            for activity in activities
        ]
    finally:
        db.close()

#Statistiken für Projekte abrufen
@app.get("/stats/projects")
def get_project_stats(
    period: str = Query(default="month"),
    selected_date: str | None = None,
    selected_month: str | None = None,
    selected_year: str | None = None,
    selected_quarter: str | None = None,
):
    db: Session = SessionLocal()
    try:
        start, end = get_period_range(period, selected_date, selected_month, selected_year, selected_quarter)
        activities = db.query(ActivityLog).all()
        projects = db.query(Project).all()

        grouped = {}
        for activity in activities:
            if activity.start_time < start or activity.start_time >= end or activity.project_id is None:
                continue

            task_name = (activity.task_text or "").strip() or "(ohne Aufgabe)"
            key = (activity.project_id, task_name, activity.start_time.date())
            if key not in grouped:
                grouped[key] = {"project_id": activity.project_id, "daily_seconds": 0}
            grouped[key]["daily_seconds"] += activity.duration_seconds

        stats_map = {
            project.id: {
                "project_id": project.id,
                "project_name": project.name,
                "color": project.color,
                "hourly_rate": project.hourly_rate or 0,
                "total_seconds_raw": 0,
                "total_seconds_billable": 0,
            }
            for project in projects
        }

        for item in grouped.values():
            project_id = item["project_id"]
            raw_seconds = item["daily_seconds"]
            billable_seconds = round_to_15_minutes(raw_seconds)
            if project_id in stats_map:
                stats_map[project_id]["total_seconds_raw"] += raw_seconds
                stats_map[project_id]["total_seconds_billable"] += billable_seconds

        return [
            {
                "project_id": item["project_id"],
                "project_name": item["project_name"],
                "color": item["color"],
                "hourly_rate": item["hourly_rate"],
                "total_seconds_raw": item["total_seconds_raw"],
                "total_hours_raw": round(item["total_seconds_raw"] / 3600, 2),
                "total_seconds_billable": item["total_seconds_billable"],
                "total_hours_billable": round(item["total_seconds_billable"] / 3600, 2),
                "revenue": round((item["total_seconds_billable"] / 3600) * item["hourly_rate"], 2),
            }
            for item in stats_map.values()
        ]
    finally:
        db.close()

#Statistiken für nicht zugeordnete Zeitblöcke abrufen
@app.get("/stats/unassigned")
def get_unassigned_stats(
    period: str = Query(default="month"),
    selected_date: str | None = None,
    selected_month: str | None = None,
    selected_year: str | None = None,
    selected_quarter: str | None = None,
):
    db: Session = SessionLocal()
    try:
        start, end = get_period_range(period, selected_date, selected_month, selected_year, selected_quarter)
        activities = db.query(ActivityLog).all()
        total_seconds = sum(
            activity.duration_seconds
            for activity in activities
            if activity.project_id is None and activity.start_time >= start and activity.start_time < end
        )

        return {"unassigned_seconds": total_seconds, "unassigned_hours": round(total_seconds / 3600, 2)}
    finally:
        db.close()

#Statistiken für Umsatz abrufen
@app.get("/stats/revenue")
def get_revenue_stats(
    period: str = Query(default="month"),
    selected_date: str | None = None,
    selected_month: str | None = None,
    selected_year: str | None = None,
    selected_quarter: str | None = None,
):
    db: Session = SessionLocal()
    try:
        start, end = get_period_range(period, selected_date, selected_month, selected_year, selected_quarter)
        activities = db.query(ActivityLog).all()
        grouped = {}

        for activity in activities:
            if activity.start_time < start or activity.start_time >= end:
                continue
            if activity.project_id is None or not activity.project:
                continue

            task_name = (activity.task_text or "").strip() or "(ohne Aufgabe)"
            key = (activity.project_id, task_name, activity.start_time.date())
            if key not in grouped:
                grouped[key] = {"daily_seconds": 0, "hourly_rate": activity.project.hourly_rate or 0}
            grouped[key]["daily_seconds"] += activity.duration_seconds

        total_revenue = 0
        for item in grouped.values():
            total_revenue += (round_to_15_minutes(item["daily_seconds"]) / 3600) * item["hourly_rate"]

        return {"total_revenue": round(total_revenue, 2)}
    finally:
        db.close()

#Statistiken für Aufgaben abrufen
@app.get("/stats/tasks")
def get_task_stats(
    period: str = Query(default="month"),
    selected_date: str | None = None,
    selected_month: str | None = None,
    selected_year: str | None = None,
    selected_quarter: str | None = None,
):
    db: Session = SessionLocal()
    try:
        start, end = get_period_range(period, selected_date, selected_month, selected_year, selected_quarter)
        activities = db.query(ActivityLog).all()
        grouped = {}

        for activity in activities:
            if activity.start_time < start or activity.start_time >= end:
                continue
            if activity.project_id is None or not activity.project:
                continue

            task_name = (activity.task_text or "").strip() or "(ohne Aufgabe)"
            key = (activity.project_id, task_name, activity.start_time.date())
            if key not in grouped:
                grouped[key] = {
                    "project_id": activity.project_id,
                    "project_name": activity.project.name,
                    "task_name": task_name,
                    "daily_seconds": 0,
                    "hourly_rate": activity.project.hourly_rate or 0,
                }
            grouped[key]["daily_seconds"] += activity.duration_seconds

        task_stats_map = {}
        for item in grouped.values():
            key = (item["project_id"], item["task_name"])
            billable_seconds = round_to_15_minutes(item["daily_seconds"])
            if key not in task_stats_map:
                task_stats_map[key] = {
                    "project_id": item["project_id"],
                    "project_name": item["project_name"],
                    "task_name": item["task_name"],
                    "hourly_rate": item["hourly_rate"],
                    "total_seconds_raw": 0,
                    "total_seconds_billable": 0,
                }

            task_stats_map[key]["total_seconds_raw"] += item["daily_seconds"]
            task_stats_map[key]["total_seconds_billable"] += billable_seconds

        result = []
        for item in task_stats_map.values():
            result.append(
                {
                    "project_id": item["project_id"],
                    "project_name": item["project_name"],
                    "task_name": item["task_name"],
                    "hourly_rate": item["hourly_rate"],
                    "total_seconds_raw": item["total_seconds_raw"],
                    "total_hours_raw": round(item["total_seconds_raw"] / 3600, 2),
                    "total_seconds_billable": item["total_seconds_billable"],
                    "total_hours_billable": round(item["total_seconds_billable"] / 3600, 2),
                    "revenue": round((item["total_seconds_billable"] / 3600) * item["hourly_rate"], 2),
                }
            )

        result.sort(key=lambda item: (item["project_name"].lower(), item["task_name"].lower()))
        return result
    finally:
        db.close()

#Statistiken für Aufgaben als CSV exportieren
@app.get("/exports/tasks")
def export_task_stats(
    period: str = Query(default="month"),
    selected_date: str | None = None,
    selected_month: str | None = None,
    selected_year: str | None = None,
    selected_quarter: str | None = None,
):
    task_stats = get_task_stats(
        period=period,
        selected_date=selected_date,
        selected_month=selected_month,
        selected_year=selected_year,
        selected_quarter=selected_quarter,
    )

    return StreamingResponse(
        iter([build_task_stats_csv(task_stats)]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=aufgaben_auswertung.csv"},
    )

#Dashboard-Seite und zugehörige Ressourcen bereitstellen
@app.get("/dashboard")
def get_dashboard():
    return FileResponse(get_resource_path("app", "dashboard.html"))

#Dashboard-CSS
@app.get("/dashboard.js")
def get_dashboard_js():
    return FileResponse(get_resource_path("app", "dashboard.js"))


