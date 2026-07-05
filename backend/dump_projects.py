"""Rebuild the frontend's baked projects.json from the seeded projects.

The deployed site reads frontend/src/projects.json (no live backend), so after
editing seed.py, run this to regenerate it:

    uv run python dump_projects.py     # from backend/
"""

import json
from datetime import datetime
from pathlib import Path

from sqlmodel import Session, SQLModel, select

from app.config import DATA_DIR, ensure_dirs
from app.db import engine
from app.models import Project
from app.seed import seed

OUT = Path(__file__).resolve().parent.parent / "frontend" / "src" / "projects.json"


def main() -> None:
    ensure_dirs()
    db_file = DATA_DIR / "portfolio.db"
    if db_file.exists():
        db_file.unlink()  # force a fresh seed from the current seed.py
    SQLModel.metadata.create_all(engine)
    seed()

    with Session(engine) as session:
        projects = session.exec(select(Project).order_by(Project.sort_order)).all()
        data = []
        for p in projects:
            row = p.model_dump()
            if isinstance(row.get("created_at"), datetime):
                row["created_at"] = row["created_at"].isoformat(sep=" ")
            data.append(row)

    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"wrote {len(data)} projects to {OUT}")


if __name__ == "__main__":
    main()
