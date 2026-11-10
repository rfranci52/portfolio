"""Visit events: POST /api/track, friendly to navigator.sendBeacon.

A normal function in one self-contained file. The client sends what happened and
the server adds the visit details it can see in the request headers. Rows go in
through a role that can insert and cannot read back, and each insert first takes
a slot from a daily limit, so this endpoint cannot be used to fill the table.
"""
import ipaddress
import json
import os
import re
import unicodedata
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler
from urllib.parse import quote, unquote, urlsplit

MAX_BODY_BYTES = 4096
MAX_DATA_BYTES = 1024
KINDS = {"pageview", "scroll", "click", "session_start", "feedback"}
SITE_ORIGIN_HOSTS = {"rakimfrancis.com", "www.rakimfrancis.com"}

_COLUMNS = (
    "kind", "visitor_id", "session_id", "turn_id", "path", "referrer", "data", "ip",
    "city", "region", "country", "network", "user_agent", "device",
)


def device_from(user_agent):
    """A simple desktop, mobile or tablet guess from the user agent."""
    agent = (user_agent or "").lower()
    if re.search(r"ipad|tablet|kindle|silk", agent) or ("android" in agent and "mobile" not in agent):
        return "tablet"
    if re.search(r"mobi|iphone|ipod|android", agent):
        return "mobile"
    return "desktop"


def network_owner(ip):
    """Name of the network behind an address, when a token is configured. Otherwise None."""
    token = os.environ.get("IPINFO_TOKEN", "")
    if not token or not ip:
        return None
    try:
        ipaddress.ip_address(ip)
        url = f"https://api.ipinfo.io/lite/{quote(ip)}?token={quote(token)}"
        with urllib.request.urlopen(url, timeout=1) as resp:
            return json.load(resp).get("as_name")
    except Exception:
        return None


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


def _short(value, limit):
    return _clean_text(value)[:limit] if isinstance(value, str) else None


def _uuid_or_none(value):
    try:
        return str(uuid.UUID(value)) if isinstance(value, str) else None
    except ValueError:
        return None


def clean_data(kind, data):
    """Only the fields each kind of event is expected to carry, within the size cap."""
    if not isinstance(data, dict):
        return {}
    cleaned = {}
    if kind == "scroll":
        depth = data.get("depth")
        if isinstance(depth, int) and not isinstance(depth, bool) and 0 <= depth <= 100:
            cleaned["depth"] = depth
    elif kind == "feedback":
        if data.get("value") in ("up", "down"):
            cleaned["value"] = data["value"]
    elif kind == "click":
        for field, limit in (("tag", 16), ("text", 80), ("href", 256)):
            value = _short(data.get(field), limit)
            if value:
                cleaned[field] = value
    if len(json.dumps(cleaned).encode("utf-8")) > MAX_DATA_BYTES:
        return {}
    return cleaned


def build_row(data, headers):
    """The row to insert, or None when the event is not one this endpoint accepts."""
    if not isinstance(data, dict) or not isinstance(data.get("kind"), str) or data["kind"] not in KINDS:
        return None
    ip = _short((headers.get("x-forwarded-for") or "").split(",")[0].strip(), 64) or None
    user_agent = _short(headers.get("user-agent") or "", 512) or None
    return {
        "kind": data["kind"],
        "visitor_id": _short(data.get("visitor_id"), 100),
        "session_id": _short(data.get("session_id"), 100),
        "turn_id": _uuid_or_none(data.get("turn_id")),
        "path": _short(data.get("path"), 512),
        "referrer": _short(data.get("referrer"), 1024),
        "data": clean_data(data["kind"], data.get("data")),
        "ip": ip,
        "city": _short(unquote(headers.get("x-vercel-ip-city") or ""), 128) or None,
        "region": _short(headers.get("x-vercel-ip-country-region") or "", 16) or None,
        "country": _short(headers.get("x-vercel-ip-country") or "", 8) or None,
        "network": None,
        "user_agent": user_agent,
        "device": device_from(user_agent),
    }


def write_event(row):
    """Insert one event if today's limits allow it. An event over a limit is dropped."""
    import psycopg
    from psycopg.types.json import Jsonb

    url = os.environ.get("SITE_LOGGER_URL", "")
    if not url:
        raise RuntimeError("database url is not set")
    sql = "insert into site.events (%s) values (%s)" % (", ".join(_COLUMNS), ", ".join(["%s"] * len(_COLUMNS)))
    with psycopg.connect(url, connect_timeout=5) as conn:
        conn.prepare_threshold = None  # needed on the pooled endpoint
        slot = conn.execute(
            "select site.take_event_slot(%s, %s, %s)",
            (
                quota_key(row["ip"] or "unknown"),
                _env_int("SITE_EVENTS_PER_VISITOR_DAILY", 300),
                _env_int("SITE_EVENTS_GLOBAL_DAILY", 20000),
            ),
        ).fetchone()
        if not slot or not slot[0]:
            return False
        if row["kind"] == "session_start":
            row["network"] = network_owner(row["ip"])
        conn.execute(sql, [Jsonb(row[col]) if col == "data" else row[col] for col in _COLUMNS])
    return True


class handler(BaseHTTPRequestHandler):
    def send_error(self, code, message=None, explain=None):
        # A short JSON reply in place of the standard library's HTML error page. A method with
        # no handler arrives here as 501; for a POST-only endpoint the right answer is 405.
        if code == 501:
            code = 405
        body = json.dumps({"error": "method not allowed" if code == 405 else "request refused"}).encode()
        self.close_connection = True
        self.send_response(code)
        if code == 405:
            self.send_header("Allow", "POST")
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if getattr(self, "command", None) != "HEAD":
            self.wfile.write(body)

    def _reply(self, status):
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        if not origin_allowed(self.headers.get("origin") or ""):
            return self._reply(403)
        try:
            length = int(self.headers.get("content-length") or 0)
        except ValueError:
            return self._reply(400)
        if not 0 <= length <= MAX_BODY_BYTES:
            return self._reply(413)
        try:
            data = json.loads(self.rfile.read(length) or b"null")
        except (ValueError, RecursionError):
            return self._reply(400)
        row = build_row(data, self.headers)
        if row is None:
            return self._reply(400)
        try:
            write_event(row)
        except Exception as exc:
            print("track: write failed:", type(exc).__name__)
        return self._reply(204)
