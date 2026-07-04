from datetime import datetime, timezone

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Project(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    slug: str = Field(unique=True, index=True)
    title: str
    tagline: str = ""          # one-line hook for cards
    summary: str = ""          # short paragraph for the card / list
    tech: list = Field(default_factory=list, sa_column=Column(JSON))       # ["FastAPI", "OpenCV", ...]
    highlights: list = Field(default_factory=list, sa_column=Column(JSON)) # bullet wins
    # Case-study body as an ordered list of sections: [{"heading", "body"}].
    sections: list = Field(default_factory=list, sa_column=Column(JSON))
    repo_url: str | None = None
    demo_url: str | None = None
    video_url: str | None = None
    featured: bool = False
    sort_order: int = 0
    created_at: datetime = Field(default_factory=utcnow)


class ContactMessage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    email: str
    message: str
    created_at: datetime = Field(default_factory=utcnow)
