"""Contact-form email delivery via Resend.

Degrades gracefully: if RESEND_API_KEY isn't set, this no-ops (the message is
still saved to the database), so local dev works without any secret.
"""

import logging

from app.config import CONTACT_TO_EMAIL, RESEND_API_KEY, RESEND_FROM

logger = logging.getLogger(__name__)


def send_contact_email(name: str, email: str, message: str) -> None:
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set; email skipped (message saved to DB)")
        return

    import resend

    resend.api_key = RESEND_API_KEY
    try:
        resend.Emails.send({
            "from": RESEND_FROM,
            "to": [CONTACT_TO_EMAIL],
            "reply_to": email,  # hit reply in your inbox → replies to the sender
            "subject": f"New portfolio message from {name}",
            "text": f"From: {name} <{email}>\n\n{message}",
        })
        logger.info("contact email sent to %s", CONTACT_TO_EMAIL)
    except Exception:
        logger.exception("failed to send contact email (message is still saved in the DB)")
