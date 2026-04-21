from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Date, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    color = Column(String, nullable=True)
    hourly_rate = Column(Float, nullable=True)

    active_from = Column(Date, nullable=True)
    active_to = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    keywords = relationship("ProjectKeyword", back_populates="project", cascade="all, delete-orphan")
    activities = relationship("ActivityLog", back_populates="project")
    tasks = relationship("ProjectTask", back_populates="project", cascade="all, delete-orphan")


class ProjectKeyword(Base):
    __tablename__ = "project_keywords"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String, nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    project = relationship("Project", back_populates="keywords")


class ProjectTask(Base):
    __tablename__ = "project_tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    project = relationship("Project", back_populates="tasks")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    app_name = Column(String, nullable=True)
    window_title = Column(String, nullable=True)

    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    duration_seconds = Column(Float, nullable=False)

    matched_keyword = Column(String, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)

    task_text = Column(String, nullable=True)
    comment_text = Column(String, nullable=True)
    needs_review = Column(Boolean, default=False, nullable=False)

    project = relationship("Project", back_populates="activities")

    