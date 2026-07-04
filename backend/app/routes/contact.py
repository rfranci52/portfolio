from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlmodel import Session

from app.db import get_session
from app.email import send_contact_email
from app.models import ContactMessage

router = APIRouter(prefix="/api/contact", tags=["contact"])


class ContactIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    message: str = Field(min_length=1, max_length=5000)


@router.post("", status_code=201)
def submit_contact(
    payload: ContactIn,
    background: BackgroundTasks,
    session: Session = Depends(get_session),
) -> dict:
    # Save first (durable backup), then email in the background so the response
    # stays instant and a mail hiccup never loses a message or errors the user.
    session.add(ContactMessage(name=payload.name, email=payload.email, message=payload.message))
    session.commit()
    background.add_task(send_contact_email, payload.name, payload.email, payload.message)
    return {"ok": True, "message": "Thanks — I'll get back to you."}
