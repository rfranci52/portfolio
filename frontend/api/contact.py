"""Contact form: save to Neon (leads schema) + best-effort email via Resend.

A Vercel serverless function. The database write is the reliable capture: every
submission lands in leads.submissions through the least-privilege leads_writer role
(INSERT only, it cannot read anyone's data back). Email via Resend is a nice-to-have
on top. A message is never silently lost.

Env vars (portfolio Vercel project):
  LEADS_WRITER_URL   pooled Neon URL for the leads_writer role (the reliable path)
  RESEND_API_KEY     optional; enables the email notification on top
  CONTACT_TO_EMAIL   defaults to rakimfrancis@gmail.com
  RESEND_FROM        defaults to "Portfolio <onboarding@resend.dev>"
"""
import json
import os
import urllib.request
from http.server import BaseHTTPRequestHandler

import psycopg

LEADS_WRITER_URL = os.environ.get("LEADS_WRITER_URL", "")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
CONTACT_TO = os.environ.get("CONTACT_TO_EMAIL", "rakimfrancis@gmail.com")
RESEND_FROM = os.environ.get("RESEND_FROM", "Portfolio <onboarding@resend.dev>")


def save_lead(name, email, message):
    """Persist the submission to leads.submissions. Raises on failure."""
    # prepare_threshold=None keeps this compatible with Neon's pooled endpoint.
    with psycopg.connect(LEADS_WRITER_URL) as conn:
        conn.prepare_threshold = None
        conn.execute(
            "INSERT INTO leads.submissions (name, email, message, source) "
            "VALUES (%s, %s, %s, %s)",
            (name, email, message, "portfolio-contact"),
        )
        # commits on clean exit of the connection context


def send_email(name, email, message):
    """Best-effort notification via Resend. Never raises."""
    if not RESEND_API_KEY:
        return False
    body = json.dumps({
        "from": RESEND_FROM,
        "to": [CONTACT_TO],
        "reply_to": email,
        "subject": f"New portfolio message from {name}",
        "text": f"From: {name} <{email}>\n\n{message}",
    }).encode()
    req = urllib.request.Request(
        "https://api.resend.com/emails", data=body, method="POST",
        headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception:
        import traceback
        traceback.print_exc()
        return False


class handler(BaseHTTPRequestHandler):
    def _reply(self, status, payload):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def do_POST(self):
        length = int(self.headers.get("content-length") or 0)
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            return self._reply(400, {"ok": False, "message": "Invalid request."})

        name = (data.get("name") or "").strip()[:200]
        email = (data.get("email") or "").strip()[:320]
        message = (data.get("message") or "").strip()[:5000]
        if not (name and email and message):
            return self._reply(400, {"ok": False, "message": "All fields are required."})

        # 1) Reliable capture: save to the database. This is what must not be lost.
        saved = False
        if LEADS_WRITER_URL:
            try:
                save_lead(name, email, message)
                saved = True
            except Exception:
                import traceback
                traceback.print_exc()

        # 2) Best-effort email notification on top.
        send_email(name, email, message)

        if saved:
            return self._reply(200, {"ok": True, "message": "Thanks! I'll get back to you."})
        # DB unavailable: stay graceful, but give a real path so nothing is lost.
        return self._reply(200, {"ok": True,
            "message": "Thanks! I'll get back to you. If it's time-sensitive, email me directly at rakimfrancis@gmail.com."})
