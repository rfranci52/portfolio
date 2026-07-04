"""Contact form -> email via Resend, as a Vercel serverless function.

Pure standard library (urllib), so there are no Python dependencies to install
on Vercel. Set RESEND_API_KEY in the Vercel project's Environment Variables and
it works. Mirrors backend/app/email.py; the FastAPI backend stays in the repo
for local dev and as the full-stack showcase.
"""

import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
CONTACT_TO = os.environ.get("CONTACT_TO_EMAIL", "rakimfrancis@gmail.com")
RESEND_FROM = os.environ.get("RESEND_FROM", "Portfolio <onboarding@resend.dev>")


class handler(BaseHTTPRequestHandler):
    def _reply(self, status: int, payload: dict) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def do_POST(self) -> None:
        length = int(self.headers.get("content-length") or 0)
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            return self._reply(400, {"ok": False, "message": "Invalid request."})

        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip()
        message = (data.get("message") or "").strip()
        if not (name and email and message):
            return self._reply(400, {"ok": False, "message": "All fields are required."})

        if not RESEND_API_KEY:
            # No key configured — accept gracefully rather than erroring the visitor.
            return self._reply(200, {"ok": True, "message": "Thanks — I'll get back to you."})

        body = json.dumps({
            "from": RESEND_FROM,
            "to": [CONTACT_TO],
            "reply_to": email,
            "subject": f"New portfolio message from {name}",
            "text": f"From: {name} <{email}>\n\n{message}",
        }).encode()
        request = urllib.request.Request(
            "https://api.resend.com/emails",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
        )
        try:
            urllib.request.urlopen(request, timeout=10)
        except Exception:
            return self._reply(502, {
                "ok": False,
                "message": "Couldn't send right now — please email rakimfrancis@gmail.com directly.",
            })
        return self._reply(200, {"ok": True, "message": "Thanks — I'll get back to you."})
