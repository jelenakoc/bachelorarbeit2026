from app.database import SessionLocal
from app.models import ActivityLog

db = SessionLocal()

activities = db.query(ActivityLog).all()

print("=== ALLE ZEITBLÖCKE ===\n")

for a in activities:
    print(f"ID: {a.id}")
    print(f"App: {a.app_name}")
    print(f"Start: {a.start_time}")
    print(f"Ende: {a.end_time}")
    print(f"Dauer: {a.duration_seconds:.2f} Sekunden")
    print(f"Matched Keyword: {a.matched_keyword}")
    print(f"Project ID: {a.project_id}")
    print("-" * 40)

db.close()