"""The contact form: who may post, what it accepts, and the daily limits in front of it."""
import io
import json

import pytest

from conftest import ROOT, load_module

ORIGIN = ("origin", "https://rakimfrancis.com")
JSON_TYPE = ("content-type", "application/json")
VALID = {"name": "Test Example", "email": "visitor@example.test", "message": "Hello there.", "extra": ""}


@pytest.fixture
def dev_api():
    return load_module(ROOT / "scripts" / "dev_api.py", "site_dev_api_for_contact_tests")


class Recorder:
    def __init__(self):
        self.order = []
        self.saved = []
        self.emailed = []
        self.slot_keys = []
        self.slot = (True, True)
        self.save_error = None
        self.email_result = (True, "sent:200")


@pytest.fixture
def contact(monkeypatch):
    module = load_module(ROOT / "frontend" / "api" / "contact.py", "site_contact_for_tests")
    log = Recorder()

    def take_slot(visitor):
        log.order.append("slot")
        log.slot_keys.append(visitor)
        if isinstance(log.slot, Exception):
            raise log.slot
        return log.slot

    def save_lead(name, email, message):
        log.order.append("save")
        if log.save_error:
            raise log.save_error
        log.saved.append((name, email, message))

    def send_email(name, email, message):
        log.order.append("email")
        log.emailed.append((name, email, message))
        return log.email_result

    monkeypatch.setattr(module, "LEADS_WRITER_URL", "postgres://example.test/db")
    monkeypatch.setattr(module, "take_slot", take_slot)
    monkeypatch.setattr(module, "save_lead", save_lead)
    monkeypatch.setattr(module, "send_email", send_email)
    monkeypatch.delenv("SITE_ALLOWED_ORIGINS", raising=False)
    module.log = log
    return module


def post(dev_api, contact, body, headers=(ORIGIN, JSON_TYPE), length=None):
    if not isinstance(body, bytes):
        body = json.dumps(body).encode()
    declared = str(len(body)) if length is None else length
    status, _, payload = dev_api.run_handler(contact.handler, "POST", "/api/contact", [("content-length", declared), *headers], body)
    return status, json.loads(payload)


def assert_nothing_happened(contact):
    assert contact.log.order == []


def test_a_valid_message_takes_a_slot_then_saves_then_emails(dev_api, contact):
    status, reply = post(dev_api, contact, VALID)
    assert status == 200 and reply["ok"] is True
    assert contact.log.order == ["slot", "save", "email"]
    assert contact.log.saved == [("Test Example", "visitor@example.test", "Hello there.")]
    assert contact.log.emailed == contact.log.saved


@pytest.mark.parametrize("origin", ["https://rakimfrancis.com", "https://www.rakimfrancis.com"])
def test_the_real_site_may_post(dev_api, contact, origin):
    assert post(dev_api, contact, VALID, headers=[("origin", origin), JSON_TYPE])[0] == 200


@pytest.mark.parametrize("headers", [
    [("origin", "https://evil.example"), JSON_TYPE],
    [("origin", "https://rakimfrancis.com.evil.example"), JSON_TYPE],
    [("origin", "https://portfolio-abc123-rakim.vercel.app"), ("x-forwarded-host", "portfolio-abc123-rakim.vercel.app"), JSON_TYPE],
    [("origin", "http://rakimfrancis.com"), JSON_TYPE],
    [("origin", "null"), JSON_TYPE],
    [JSON_TYPE],
])
def test_everything_but_the_real_site_is_refused(dev_api, contact, headers):
    status, reply = post(dev_api, contact, VALID, headers=headers)
    assert status == 403 and reply["ok"] is False
    assert_nothing_happened(contact)


def test_a_configured_local_host_may_post(dev_api, contact, monkeypatch):
    monkeypatch.setenv("SITE_ALLOWED_ORIGINS", "localhost,127.0.0.1")
    assert post(dev_api, contact, VALID, headers=[("origin", "http://localhost:5173"), JSON_TYPE])[0] == 200


@pytest.mark.parametrize("content_type", ["text/plain", "application/x-www-form-urlencoded", "multipart/form-data; boundary=x", "application/jsonx"])
def test_only_json_is_accepted(dev_api, contact, content_type):
    assert post(dev_api, contact, VALID, headers=[ORIGIN, ("content-type", content_type)])[0] == 415
    assert_nothing_happened(contact)


def test_a_missing_content_type_is_refused(dev_api, contact):
    assert post(dev_api, contact, VALID, headers=[ORIGIN])[0] == 415


@pytest.mark.parametrize("content_type", ["application/json; charset=utf-8", "Application/JSON"])
def test_json_with_a_charset_or_capitals_is_accepted(dev_api, contact, content_type):
    assert post(dev_api, contact, VALID, headers=[ORIGIN, ("content-type", content_type)])[0] == 200


def test_a_body_over_the_cap_is_refused_before_it_is_read(contact):
    class Unreadable(io.BytesIO):
        def read(self, *args):
            raise AssertionError("the body was read")

    request = contact.handler.__new__(contact.handler)
    request.headers = {"content-type": "application/json", "content-length": str(contact.MAX_BODY_BYTES + 1)}
    request.rfile = Unreadable(b"")
    assert request._read_json() == (None, 413)


def test_a_body_over_the_cap_gets_a_way_to_reach_him(dev_api, contact):
    body = json.dumps({**VALID, "message": "m" * (contact.MAX_BODY_BYTES + 1)}).encode()
    status, reply = post(dev_api, contact, body)
    assert status == 413 and contact.DIRECT_EMAIL in reply["message"]
    assert_nothing_happened(contact)


def test_a_body_at_the_cap_is_read(dev_api, contact):
    body = json.dumps({**VALID, "message": "m" * (contact.MAX_BODY_BYTES - 200)}).encode()
    assert len(body) <= contact.MAX_BODY_BYTES
    assert post(dev_api, contact, body)[0] == 200
    assert len(contact.log.saved[0][2]) == contact.MAX_MESSAGE_CHARS


@pytest.mark.parametrize("length", ["abc", "-1", "1.5"])
def test_a_bad_length_is_refused(dev_api, contact, length):
    assert post(dev_api, contact, b"{}", length=length)[0] == 400
    assert_nothing_happened(contact)


@pytest.mark.parametrize("body", [b"not json", b"[]", b"[1, 2]", b'"text"', b"5", b"null", b"", b"\xff\xfe", b"[" * 8000])
def test_a_body_that_is_not_an_object_is_refused(dev_api, contact, body):
    status, reply = post(dev_api, contact, body)
    assert status == 400 and reply["ok"] is False
    assert_nothing_happened(contact)


@pytest.mark.parametrize("field", ["name", "email", "message", "extra"])
@pytest.mark.parametrize("value", [[], {}, 5, True, None])
def test_a_field_that_is_not_text_is_refused(dev_api, contact, field, value):
    assert post(dev_api, contact, {**VALID, field: value})[0] == 400
    assert_nothing_happened(contact)


@pytest.mark.parametrize("field", ["name", "email", "message"])
@pytest.mark.parametrize("value", ["", "   ", "\x00\x01"])
def test_an_empty_field_is_refused(dev_api, contact, field, value):
    status, reply = post(dev_api, contact, {**VALID, field: value})
    assert status == 400 and reply["message"] == "All fields are required."
    assert_nothing_happened(contact)


def test_a_filled_honeypot_looks_accepted_and_does_nothing(dev_api, contact):
    status, reply = post(dev_api, contact, {**VALID, "extra": "https://spam.example"})
    assert (status, reply) == (200, {"ok": True, "message": contact.THANKS})
    assert_nothing_happened(contact)


def test_a_page_from_before_the_honeypot_still_works(dev_api, contact):
    body = {key: value for key, value in VALID.items() if key != "extra"}
    assert post(dev_api, contact, body)[0] == 200
    assert contact.log.saved


def test_control_characters_are_removed_and_line_breaks_kept_in_the_message(dev_api, contact):
    body = {**VALID, "name": "Te\x00st\x1b[2J", "message": "Line one\nLine\ttwo\x00\x07\ud800"}
    assert post(dev_api, contact, body)[0] == 200
    name, _, message = contact.log.saved[0]
    assert name == "Test[2J"
    assert message == "Line one\nLine\ttwo"


@pytest.mark.parametrize("name,expected", [
    ("Test\r\nBcc: other@example.test", "Test Bcc: other@example.test"),
    ("Test\rExample", "Test Example"),
    ("Test\nExample", "Test Example"),
    ("Test\u2028Example", "Test Example"),
    ("Test   Example", "Test Example"),
])
def test_line_breaks_are_stripped_from_the_name(dev_api, contact, name, expected):
    assert post(dev_api, contact, {**VALID, "name": name})[0] == 200
    assert contact.log.saved[0][0] == expected
    assert contact.log.emailed[0][0] == expected


def test_line_breaks_at_the_end_of_the_address_are_stripped(dev_api, contact):
    assert post(dev_api, contact, {**VALID, "email": "visitor@example.test\r\n"})[0] == 200
    assert contact.log.saved[0][1] == "visitor@example.test"


@pytest.mark.parametrize("email", [
    "visitor@example.test\r\nBcc: other@example.test",
    "not an address", "visitor", "visitor@", "@example.test", "visitor@example", "visitor@@example.test", "a@b@example.test",
    "visitor example@example.test", "<visitor@example.test>", "Test <visitor@example.test>", "visitor@example.test, other@example.test",
    "visitor@.test", "visitor@example.", "visitor@exa mple.test", "x" * 320 + "@example.test",
])
def test_an_address_of_the_wrong_shape_is_refused(dev_api, contact, email):
    status, reply = post(dev_api, contact, {**VALID, "email": email})
    assert status == 400 and reply["message"] == "Please enter a valid email address."
    assert_nothing_happened(contact)


@pytest.mark.parametrize("email", [
    "visitor@example.test", "first.last+tag@mail.example.co.uk", "o'brien@example.test", "user_1-x@sub-domain.example.test",
    "jos\u00e9@example.test", "visitor@ex\u00e4mple.test",
])
def test_real_addresses_are_accepted(dev_api, contact, email):
    assert post(dev_api, contact, {**VALID, "email": email})[0] == 200
    assert contact.log.saved[0][1] == email


def test_over_the_limit_nothing_is_saved_or_sent_and_the_visitor_is_told(dev_api, contact):
    contact.log.slot = (False, False)
    status, reply = post(dev_api, contact, VALID)
    assert status == 429 and reply["ok"] is False and contact.DIRECT_EMAIL in reply["message"]
    assert contact.log.order == ["slot"]


def test_the_slot_is_counted_against_the_first_forwarded_address(dev_api, contact):
    post(dev_api, contact, VALID, headers=[ORIGIN, JSON_TYPE, ("x-forwarded-for", "203.0.113.5, 10.0.0.2")])
    assert contact.log.slot_keys == ["203.0.113.5"]


def test_the_slot_groups_an_ipv6_visitor(dev_api, contact):
    post(dev_api, contact, VALID, headers=[ORIGIN, JSON_TYPE, ("x-forwarded-for", "2001:db8:1:2:aaaa:bbbb:cccc:dddd")])
    assert contact.log.slot_keys == ["2001:db8:1:2::/64"]


def test_a_message_is_kept_when_the_limit_check_fails(dev_api, contact):
    contact.log.slot = RuntimeError("database is down")
    status, reply = post(dev_api, contact, VALID)
    assert status == 200 and reply["ok"] is True
    assert contact.log.order == ["slot", "save", "email"]


def test_past_the_email_cap_a_message_is_saved_without_an_email(dev_api, contact):
    contact.log.slot = (True, False)
    status, reply = post(dev_api, contact, VALID)
    assert status == 200 and reply["ok"] is True
    assert contact.log.order == ["slot", "save"]


def test_a_saved_message_succeeds_when_the_email_fails(dev_api, contact):
    contact.log.email_result = (False, "http:500:nope")
    status, reply = post(dev_api, contact, VALID)
    assert (status, reply["ok"]) == (200, True)


def test_an_emailed_message_succeeds_when_the_save_fails(dev_api, contact):
    contact.log.save_error = RuntimeError("database is down")
    status, reply = post(dev_api, contact, VALID)
    assert (status, reply["ok"]) == (200, True)
    assert contact.DIRECT_EMAIL in reply["message"]


def test_when_both_save_and_email_fail_the_visitor_is_told_to_email_directly(dev_api, contact):
    contact.log.save_error = RuntimeError("database is down")
    contact.log.email_result = (False, "no_key")
    status, reply = post(dev_api, contact, VALID)
    assert status == 503 and reply["ok"] is False
    assert contact.DIRECT_EMAIL in reply["message"]


def test_a_failed_save_past_the_email_cap_is_reported_too(dev_api, contact):
    contact.log.slot = (True, False)
    contact.log.save_error = RuntimeError("database is down")
    assert post(dev_api, contact, VALID)[0] == 503
    assert contact.log.order == ["slot", "save"]


def test_with_no_database_configured_only_the_email_path_is_used(dev_api, contact, monkeypatch):
    monkeypatch.setattr(contact, "LEADS_WRITER_URL", "")
    assert post(dev_api, contact, VALID)[0] == 200
    assert contact.log.order == ["email"]


class FakeConn:
    def __init__(self, row=(True, True)):
        self.row = row
        self.statements = []
        self.prepare_threshold = 1

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params):
        self.statements.append((sql, params))
        return self

    def fetchone(self):
        return self.row


@pytest.fixture
def real_slot(monkeypatch):
    import psycopg

    module = load_module(ROOT / "frontend" / "api" / "contact.py", "site_contact_real_slot")
    conn = FakeConn()
    monkeypatch.setattr(psycopg, "connect", lambda *args, **kwargs: conn)
    monkeypatch.setattr(module, "LEADS_WRITER_URL", "postgres://example.test/db")
    for name in ("CONTACT_PER_VISITOR_DAILY", "CONTACT_GLOBAL_DAILY", "CONTACT_EMAIL_DAILY"):
        monkeypatch.delenv(name, raising=False)
    return module, conn


def test_the_slot_function_gets_the_default_limits(real_slot):
    module, conn = real_slot
    assert module.take_slot("203.0.113.5") == (True, True)
    sql, params = conn.statements[0]
    assert "leads.take_submission_slot" in sql
    assert params == ("203.0.113.5", 5, 50, 20)
    assert conn.prepare_threshold is None


def test_the_limits_come_from_the_environment(real_slot, monkeypatch):
    module, conn = real_slot
    monkeypatch.setenv("CONTACT_PER_VISITOR_DAILY", "2")
    monkeypatch.setenv("CONTACT_GLOBAL_DAILY", "3")
    monkeypatch.setenv("CONTACT_EMAIL_DAILY", "4")
    module.take_slot("x")
    assert conn.statements[0][1] == ("x", 2, 3, 4)


def test_the_email_request_carries_no_line_break_in_its_headers(dev_api, monkeypatch):
    import urllib.request

    module = load_module(ROOT / "frontend" / "api" / "contact.py", "site_contact_real_email")
    sent = []

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def urlopen(request, timeout):
        sent.append(json.loads(request.data))
        return Response()

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(module, "RESEND_API_KEY", "placeholder")
    monkeypatch.setattr(module, "LEADS_WRITER_URL", "")
    monkeypatch.delenv("SITE_ALLOWED_ORIGINS", raising=False)
    body = {**VALID, "name": "Test\r\nX-Injected: yes", "email": "visitor@example.test\r\n"}
    assert post(dev_api, module, body)[0] == 200
    assert "\r" not in sent[0]["subject"] and "\n" not in sent[0]["subject"]
    assert sent[0]["reply_to"] == "visitor@example.test"


# ------------------------------------------------------------ the migration file

def migration_text():
    return (ROOT / "db" / "leads_limits.sql").read_text(encoding="utf-8")


def test_the_migration_can_be_run_again():
    sql = migration_text()
    assert "create table if not exists leads.submission_limits" in sql
    assert "create or replace function leads.take_submission_slot(" in sql
    assert "drop " not in sql.lower()


def test_the_writer_reaches_the_counters_only_through_the_function():
    sql = migration_text()
    assert "revoke all on leads.submission_limits from public, leads_writer, leads_reader;" in sql
    signature = "leads.take_submission_slot(text, int, int, int)"
    assert f"revoke execute on function {signature} from public;" in sql
    assert f"grant execute on function {signature} to leads_writer;" in sql
    assert sql.count("grant ") == 1


def test_the_function_is_a_definer_with_a_fixed_search_path():
    sql = migration_text()
    assert "security definer" in sql
    assert "set search_path = leads, pg_temp" in sql
    assert "execute format" not in sql


def test_the_function_counts_visitor_global_and_email_separately():
    sql = migration_text()
    assert "where q.n < per_visitor" in sql and "where q.n < global_limit" in sql and "where q.n < email_limit" in sql
    assert sql.index("where q.n < per_visitor") < sql.index("where q.n < global_limit") < sql.index("where q.n < email_limit")
