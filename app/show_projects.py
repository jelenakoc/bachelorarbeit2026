from app.database import SessionLocal
from app.models import Project

db = SessionLocal()

projects = db.query(Project).all()

for project in projects:
    print(f"Projekt {project.id}: {project.name}")
    print(f"  Aktiv von: {project.active_from}")
    print(f"  Aktiv bis: {project.active_to}")
    print(f"  Aktiv?: {project.is_active}")
    for keyword in project.keywords:
        print(f"  - Keyword: {keyword.keyword}")
    print("-" * 40)

db.close()