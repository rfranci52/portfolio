"""Contact form: save to Neon (leads schema) + best-effort email via Resend.

A Vercel serverless function. The database write is the reliable capture: every
submission lands in leads.submissions through the least-privilege leads_writer role
(INSERT only, it cannot read anyone's data back). Email via Resend is a nice-to-have
on top. A message is never silently lost: when neither path works, the sender is told.

Only pages on the real site may post, as JSON and within a size cap. Each accepted
submission first takes a slot from daily limits kept in the database.

Env vars (portfolio Vercel project):
  LEADS_WRITER_URL   pooled Neon URL for the leads_writer role (the reliable path)
  RESEND_API_KEY     optional; enables the email notification on top
  CONTACT_TO_EMAIL   defaults to rakimfrancis@gmail.com
  RESEND_FROM        defaults to "Portfolio <onboarding@resend.dev>"
  CONTACT_PER_VISITOR_DAILY, CONTACT_GLOBAL_DAILY, CONTACT_EMAIL_DAILY   daily limits
"""
import ipaddress
import json
import os
import re
import unicodedata
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlsplit

import psycopg

LEADS_WRITER_URL = os.environ.get("LEADS_WRITER_URL", "")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
CONTACT_TO = os.environ.get("CONTACT_TO_EMAIL", "rakimfrancis@gmail.com")
RESEND_FROM = os.environ.get("RESEND_FROM", "Portfolio <onboarding@resend.dev>")

MAX_BODY_BYTES = 16 * 1024
MAX_NAME_CHARS = 200
MAX_EMAIL_CHARS = 320
MAX_MESSAGE_CHARS = 5000
SITE_ORIGIN_HOSTS = {"rakimfrancis.com", "www.rakimfrancis.com"}
HONEYPOT_FIELD = "extra"  # hidden on the page, so a person never fills it in

DIRECT_EMAIL = "rakimfrancis@gmail.com"
THANKS = "Thanks! I'll get back to you."
THANKS_NOT_SAVED = f"Thanks! I'll get back to you. If it's time-sensitive, email me directly at {DIRECT_EMAIL}."
INVALID = "Invalid request."
EMAIL_DIRECTLY = f"That message could not be sent from here. Please email me directly at {DIRECT_EMAIL}."
OVER_LIMIT = f"Too many messages have been sent from here today. Please email me directly at {DIRECT_EMAIL}."
NOT_DELIVERED = f"That message did not go through. Please email me directly at {DIRECT_EMAIL}."

_UNSAFE = r'\s@<>()\[\],;:"\\'
_EMAIL_SHAPE = re.compile(rf"[^{_UNSAFE}]+@[^{_UNSAFE}.]+(?:\.[^{_UNSAFE}.]+)+")


def origin_allowed(origin):
    """Only pages on the real site may call this, plus hosts named for local testing.

    The request's own Host is never trusted, so a generated deployment address is
    refused. A request with no Origin header is refused too.
    """
    try:
        parts = urlsplit((origin or "").strip())
        host = (parts.hostname or "").lower()
    except ValueError:
        return False
    netloc = parts.netloc.lower()
    if not host:
        return False
    if parts.scheme.lower() == "https" and netloc == host and host in SITE_ORIGIN_HOSTS:
        return True
    extra = {item.strip().lower().split("://")[-1].rstrip("/") for item in os.environ.get("SITE_ALLOWED_ORIGINS", "").split(",")}
    extra.discard("")
    return netloc in extra or host in extra


def is_json(content_type):
    return (content_type or "").split(";", 1)[0].strip().lower() == "application/json"


def quota_key(ip):
    """What a daily limit counts against. An IPv6 host usually holds a whole /64, so that is one visitor."""
    try:
        parsed = ipaddress.ip_address(ip)
    except ValueError:
        return ip
    if parsed.version == 6:
        if parsed.ipv4_mapped:
            return str(parsed.ipv4_mapped)
        return str(ipaddress.ip_network(f"{parsed}/64", strict=False))
    return ip


def _env_int(name, default):
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _clean_text(value):
    """Text that is safe to store and to print: no control characters or lone surrogates."""
    if value.isprintable():
        return value
    return "".join(ch for ch in value if ch in "\t\n\r" or unicodedata.category(ch) not in ("Cc", "Cs"))


def read_fields(data):
    """The submitted fields as cleaned strings, or None when the body is not the expected shape.

    A field left out counts as empty. Name and email lose every line break, because
    both end up in the notification email's headers.
    """
    if not isinstance(data, dict):
        return None
    fields = {}
    for key in ("name", "email", "message", HONEYPOT_FIELD):
        value = data.get(key, "")
        if not isinstance(value, str):
            return None
        fields[key] = _clean_text(value)
    fields["name"] = " ".join(fields["name"].split())[:MAX_NAME_CHARS]
    fields["email"] = fields["email"].replace("\r", "").replace("\n", "").strip()
    fields["message"] = fields["message"].strip()[:MAX_MESSAGE_CHARS]
    return fields


def valid_email(email):
    return len(email) <= MAX_EMAIL_CHARS and _EMAIL_SHAPE.fullmatch(email) is not None


def take_slot(visitor):
    """(allowed, notify) for one submission from this visitor. Raises if the check cannot run."""
    with psycopg.connect(LEADS_WRITER_URL, connect_timeout=5) as conn:
        conn.prepare_threshold = None
        row = conn.execute(
            "select allowed, notify from leads.take_submission_slot(%s, %s, %s, %s)",
            (
                visitor,
                _env_int("CONTACT_PER_VISITOR_DAILY", 5),
                _env_int("CONTACT_GLOBAL_DAILY", 50),
                _env_int("CONTACT_EMAIL_DAILY", 20),
            ),
        ).fetchone()
    return bool(row[0]), bool(row[1])


def save_lead(name, email, message):
    """Persist the submission to leads.submissions. Raises on failure."""
    # prepare_threshold=None keeps this compatible with Neon's pooled endpoint.
    with psycopg.connect(LEADS_WRITER_URL, connect_timeout=5) as conn:
        conn.prepare_threshold = None
        conn.execute(
            "INSERT INTO leads.submissions (name, email, message, source) "
            "VALUES (%s, %s, %s, %s)",
            (name, email, message, "portfolio-contact"),
        )
        # commits on clean exit of the connection context


def send_email(name, email, message):
    """Best-effort notification via Resend. Never raises. Returns (ok, detail)."""
    if not RESEND_API_KEY:
        return False, "no_key"
    body = json.dumps({
        "from": RESEND_FROM,
        "to": [CONTACT_TO],
        "reply_to": email,
        "subject": f"New portfolio message from {name}",
        "text": f"From: {name} <{email}>\n\n{message}",
    }).encode()
    req = urllib.request.Request(
        "https://api.resend.com/emails", data=body, method="POST",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            # Resend's edge (Cloudflare) 403s the default Python-urllib signature
            # with error 1010; a normal user-agent clears the browser-integrity check.
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return True, f"sent:{r.status}"
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", "replace")[:300]
        except Exception:
            detail = ""
        return False, f"http:{e.code}:{detail}"
    except Exception as e:
        return False, f"err:{type(e).__name__}:{e}"


class handler(BaseHTTPRequestHandler):
    def _reply(self, status, payload):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def _refuse(self, status, message):
        return self._reply(status, {"ok": False, "message": message})

    def _read_json(self):
        """(body, None) when the request can be read, or (None, the status to refuse it with)."""
        if not is_json(self.headers.get("content-type")):
            return None, 415
        try:
            length = int(self.headers.get("content-length") or 0)
        except ValueError:
            return None, 400
        if length < 0:
            return None, 400
        if length > MAX_BODY_BYTES:
            return None, 413
        try:
            return json.loads(self.rfile.read(length) or b"null"), None
        except (ValueError, RecursionError):
            return None, 400

    def do_POST(self):
        if not origin_allowed(self.headers.get("origin") or ""):
            return self._refuse(403, EMAIL_DIRECTLY)
        data, refused = self._read_json()
        if refused:
            return self._refuse(refused, EMAIL_DIRECTLY if refused == 413 else INVALID)
        fields = read_fields(data)
        if fields is None:
            return self._refuse(400, INVALID)
        if fields[HONEYPOT_FIELD]:  # looks accepted, so an automated sender learns nothing
            return self._reply(200, {"ok": True, "message": THANKS})
        name, email, message = fields["name"], fields["email"], fields["message"]
        if not (name and email and message):
            return self._refuse(400, "All fields are required.")
        if not valid_email(email):
            return self._refuse(400, "Please enter a valid email address.")

        # A real message is never dropped because the counters are unavailable.
        allowed, notify = True, True
        if LEADS_WRITER_URL:
            forwarded = (self.headers.get("x-forwarded-for") or "").split(",")[0].strip()
            try:
                allowed, notify = take_slot(quota_key(_clean_text(forwarded)[:64] or "unknown"))
            except Exception as exc:
                print("contact: limit check failed:", type(exc).__name__)
        if not allowed:
            return self._refuse(429, OVER_LIMIT)

        # 1) Reliable capture: save to the database. This is what must not be lost.
        saved = False
        if LEADS_WRITER_URL:
            try:
                save_lead(name, email, message)
                saved = True
            except Exception:
                import traceback
                traceback.print_exc()

        # 2) Best-effort email notification on top; log server-side but never fail on it alone.
        email_ok = False
        if notify:
            email_ok, email_detail = send_email(name, email, message)
            if not email_ok:
                print("contact: email notify failed:", email_detail)

        if saved:
            return self._reply(200, {"ok": True, "message": THANKS})
        if email_ok:  # DB unavailable: stay graceful, but give a real path so nothing is lost.
            return self._reply(200, {"ok": True, "message": THANKS_NOT_SAVED})
        return self._refuse(503, NOT_DELIVERED)
