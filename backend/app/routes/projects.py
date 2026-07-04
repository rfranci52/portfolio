from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import Project

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("")
def list_projects(session: Session = Depends(get_session)) -> list[Project]:
    return session.exec(select(Project).order_by(Project.sort_order)).all()


@router.get("/{slug}")
def get_project(slug: str, session: Session = Depends(get_session)) -> Project:
    project = session.exec(select(Project).where(Project.slug == slug)).first()
    if project is None:
        raise HTTPException(404, "Project not found")
    return project
