"""The HTTP surface: the chat ASGI app, the track function and the local router."""
import asyncio
import json

import pytest

from conftest import ROOT, load_module, model_turn

ORIGIN = b"https://rakimfrancis.com"


def call_app(app, method="POST", path="/api/chat", headers=(), body=b"{}", chunked=False):
    sent = []
    pieces = [body[i:i + 7] for i in range(0, len(body), 7)] if chunked else [body]

    async def receive():
        chunk = pieces.pop(0)
        return {"type": "http.request", "body": chunk, "more_body": bool(pieces)}

    async def send(message):
        sent.append(message)

    scope = {"type": "http", "method": method, "path": path, "headers": list(headers), "client": ("198.51.100.7", 1234)}
    asyncio.run(app(scope, receive, send))
    start = next(m for m in sent if m["type"] == "http.response.start")
    payload = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    return start["status"], dict(start["headers"]), payload, sent


def chat_body(text="What has he built?", **extra):
    return json.dumps({"messages": [{"role": "user", "content": text}], "session_id": "s", "visitor_id": "v", "page": "/", "referrer": "", **extra}).encode()


def same_origin_headers(*extra):
    return [(b"host", b"rakimfrancis.com"), (b"origin", ORIGIN), *extra]


def parse_frames(payload):
    text = payload.decode()
    assert text.endswith("\n\n")
    frames = text[:-2].split("\n\n")
    assert all(frame.startswith("data: ") for frame in frames)
    return [json.loads(frame[6:]) for frame in frames]


def test_app_streams_a_proper_event_stream(deps, chat):
    deps.script(model_turn(["He built a desktop automation engine ", "and several other useful tools."]))
    status, headers, payload, sent = call_app(chat.app, headers=same_origin_headers(), body=chat_body(), chunked=True)
    assert status == 200
    assert headers[b"content-type"] == b"text/event-stream"
    assert headers[b"cache-control"] == b"no-cache, no-transform"
    assert headers[b"x-accel-buffering"] == b"no"
    events = parse_frames(payload)
    assert [e["type"] for e in events][:3] == ["status", "passages", "status"]
    assert events[-1]["type"] == "done"
    assert sent[-1] == {"type": "http.response.body", "body": b"", "more_body": False}
    assert all(m.get("more_body") for m in sent[1:-1])


def test_app_passes_visit_details_through(deps, chat):
    deps.script(model_turn(["He built a desktop automation engine for this."]))
    headers = same_origin_headers(
        (b"x-forwarded-for", b"203.0.113.50, 10.0.0.1"),
        (b"x-vercel-ip-city", b"New%20York"),
        (b"x-vercel-ip-country-region", b"NY"),
        (b"x-vercel-ip-country", b"US"),
        (b"user-agent", b"pytest-agent"),
    )
    call_app(chat.app, headers=headers, body=chat_body())
    row = deps.logged[0]
    assert deps.quota_calls == ["203.0.113.50"]
    assert row["ip"] == "203.0.113.50" and row["city"] == "New York"
    assert row["region"] == "NY" and row["country"] == "US" and row["user_agent"] == "pytest-agent"


@pytest.mark.parametrize("origin", [b"https://evil.example", b"https://rakimfrancis.com.evil.example", b"null", b"http://localhost:5173"])
def test_app_rejects_a_foreign_origin(deps, chat, origin):
    status, _, _, _ = call_app(chat.app, headers=[(b"host", b"rakimfrancis.com"), (b"origin", origin)], body=chat_body())
    assert status == 403
    assert deps.quota_calls == [] and deps.client.requests == []


@pytest.mark.parametrize("origin", [b"https://rakimfrancis.com", b"https://www.rakimfrancis.com"])
def test_app_serves_the_real_site(deps, chat, origin):
    deps.script(model_turn(["He built a desktop automation engine for this."]))
    headers = [(b"host", b"internal.example"), (b"origin", origin)]
    assert call_app(chat.app, headers=headers, body=chat_body())[0] == 200


@pytest.mark.parametrize("origin", [
    b"https://portfolio-abc123-rakim.vercel.app",
    b"https://rakimfrancis.vercel.app",
    b"https://preview.tmp.now",
    b"http://rakimfrancis.com",
    b"https://user@rakimfrancis.com",
])
def test_a_generated_deployment_address_is_refused(deps, chat, origin):
    host = origin.split(b"//")[1]
    headers = [(b"host", host), (b"x-forwarded-host", host), (b"origin", origin)]
    status, _, payload, _ = call_app(chat.app, headers=headers, body=chat_body())
    assert status == 403
    assert deps.quota_calls == [] and deps.client.requests == []
    assert b"vercel" not in payload and b"tmp.now" not in payload


def test_the_request_host_never_grants_access(deps, chat):
    headers = [(b"host", b"sneaky.example"), (b"x-forwarded-host", b"sneaky.example"), (b"origin", b"https://sneaky.example")]
    assert call_app(chat.app, headers=headers, body=chat_body())[0] == 403


@pytest.mark.parametrize("path_headers", [
    [(b"origin", b"https://nope.vercel.app")],
    [(b"origin", ORIGIN)],
])
def test_no_response_ever_echoes_the_host(deps, chat, path_headers):
    deps.script(model_turn(["He built a desktop automation engine for this."]))
    secret = b"abc123-deploy.vercel.app"
    headers = [(b"host", secret), (b"x-forwarded-host", secret), *path_headers]
    status, response_headers, payload, _ = call_app(chat.app, headers=headers, body=chat_body())
    assert secret not in payload
    assert not any(secret in value for value in response_headers.values())
    assert status in (200, 403)


@pytest.mark.parametrize("configured", ["http://localhost:5173", "localhost:5173", "localhost"])
def test_a_configured_host_is_allowed_however_it_is_written(chat, monkeypatch, configured):
    monkeypatch.setenv("SITE_ALLOWED_ORIGINS", f"example.test, {configured}")
    assert chat.origin_allowed("http://localhost:5173")
    assert not chat.origin_allowed("http://localhost.evil.example:5173")


def test_app_accepts_a_configured_dev_origin(deps, chat, monkeypatch):
    monkeypatch.setenv("SITE_ALLOWED_ORIGINS", "http://localhost:5173")
    deps.script(model_turn(["He built a desktop automation engine for this."]))
    headers = [(b"host", b"127.0.0.1:8787"), (b"origin", b"http://localhost:5173")]
    assert call_app(chat.app, headers=headers, body=chat_body())[0] == 200


def test_app_refuses_a_request_with_no_origin(deps, chat):
    assert call_app(chat.app, headers=[(b"host", b"rakimfrancis.com")], body=chat_body())[0] == 403
    assert deps.quota_calls == []


def test_local_development_still_gets_through(chat, dev_api, monkeypatch):
    monkeypatch.setenv("SITE_ALLOWED_ORIGINS", "placeholder")
    monkeypatch.delenv("SITE_ALLOWED_ORIGINS")
    dev_api.load_env([])
    assert chat.origin_allowed("http://localhost:5173")
    assert chat.origin_allowed("http://127.0.0.1:5174")
    assert not chat.origin_allowed("https://rakimfrancis.vercel.app")


def test_app_rejects_wrong_method(deps, chat):
    assert call_app(chat.app, method="GET", headers=same_origin_headers())[0] == 405


@pytest.mark.parametrize("body", [b"not json", b"[1, 2]", b'"text"'])
def test_app_rejects_bad_json(deps, chat, body):
    assert call_app(chat.app, headers=same_origin_headers(), body=body)[0] == 400


def test_app_rejects_deep_nesting_cleanly(deps, chat):
    assert call_app(chat.app, headers=same_origin_headers(), body=b"[" * 30000)[0] == 400


def test_app_rejects_an_oversized_body(deps, chat):
    assert chat.MAX_BODY_BYTES == 64 * 1024
    assert call_app(chat.app, headers=same_origin_headers(), body=b"x" * 70000, chunked=True)[0] == 413
    assert deps.quota_calls == []


def test_app_accepts_a_body_of_a_long_conversation(deps, chat):
    deps.script(model_turn(["He built a tool for this purpose."]))
    body = chat_body("What has he built? " + "x" * 50000)
    assert 40000 < len(body) < chat.MAX_BODY_BYTES
    assert call_app(chat.app, headers=same_origin_headers(), body=body)[0] == 200


def test_app_handles_lifespan(chat):
    incoming = [{"type": "lifespan.startup"}, {"type": "lifespan.shutdown"}]
    sent = []

    async def receive():
        return incoming.pop(0)

    async def send(message):
        sent.append(message["type"])

    asyncio.run(chat.app({"type": "lifespan"}, receive, send))
    assert sent == ["lifespan.startup.complete", "lifespan.shutdown.complete"]


def run_with_disconnect(chat, deps, stop):
    """Runs a turn on a connection that reports the visitor has gone."""
    deps.script(model_turn([f"word{index} " for index in range(60)]))
    gave_body = []

    async def receive():
        if not gave_body:
            gave_body.append(True)
            return {"type": "http.request", "body": chat_body(), "more_body": False}
        return {"type": "http.disconnect"}

    sent = []

    async def send(message):
        sent.append(message)
        await asyncio.sleep(0)

    scope = {"type": "http", "method": "POST", "path": "/api/chat", "headers": same_origin_headers(), "client": None}
    asyncio.run(chat.app(scope, receive, send))
    return sent


def test_a_disconnect_is_only_noted_unless_stopping_is_switched_on(deps, chat):
    run_with_disconnect(chat, deps, stop=False)
    assert deps.client.streams[0].consumed == deps.client.streams[0].scripted.events.__len__()
    assert deps.logged[0]["outcome"] == "answered"
    assert "client_gone" in deps.logged[0]["flags"]


def test_stopping_on_disconnect_stops_the_model_call(deps, chat, monkeypatch):
    monkeypatch.setenv("SITE_STOP_ON_DISCONNECT", "1")
    run_with_disconnect(chat, deps, stop=True)
    assert deps.client.streams[0].consumed < deps.client.streams[0].scripted.events.__len__()
    assert deps.logged[0]["outcome"] == "aborted"
    assert deps.spend_recorded


def test_a_failed_send_still_logs_the_turn(deps, chat):
    deps.script(model_turn(["He built a desktop automation engine and more words follow it here."]))
    outgoing = []

    async def receive():
        return {"type": "http.request", "body": chat_body(), "more_body": False}

    async def send(message):
        outgoing.append(message)
        if len(outgoing) > 2:
            raise ConnectionError("visitor went away")

    scope = {"type": "http", "method": "POST", "path": "/api/chat", "headers": same_origin_headers(), "client": None}
    with pytest.raises(ConnectionError):
        asyncio.run(chat.app(scope, receive, send))
    assert len(deps.logged) == 1


# ------------------------------------------------------------ /api/track and the local router

@pytest.fixture
def track(monkeypatch):
    module = load_module(ROOT / "frontend" / "api" / "track.py", "site_track_for_tests")
    module.written = []
    monkeypatch.setattr(module, "write_event", module.written.append)
    monkeypatch.delenv("IPINFO_TOKEN", raising=False)
    monkeypatch.delenv("SITE_ALLOWED_ORIGINS", raising=False)
    return module


@pytest.fixture
def dev_api():
    return load_module(ROOT / "scripts" / "dev_api.py", "site_dev_api_for_tests")


SITE_ORIGIN = ("origin", "https://rakimfrancis.com")


def post_track(dev_api, track, body, headers=(SITE_ORIGIN,)):
    base = [("host", "rakimfrancis.com"), ("content-length", str(len(body)))]
    return dev_api.run_handler(track.handler, "POST", "/api/track", base + list(headers), body)


def event(**fields):
    return json.dumps({"kind": "pageview", "visitor_id": "v1", "session_id": "s1", "path": "/projects", **fields}).encode()


def test_track_records_a_pageview_with_server_details(dev_api, track):
    status, _, payload = post_track(dev_api, track, event(kind="scroll", data={"depth": 50}), headers=[
        SITE_ORIGIN,
        ("x-forwarded-for", "203.0.113.5, 10.0.0.2"),
        ("x-vercel-ip-city", "S%C3%A3o%20Paulo"),
        ("x-vercel-ip-country-region", "SP"),
        ("x-vercel-ip-country", "BR"),
        ("user-agent", "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"),
    ])
    assert status == 204 and payload == b""
    row = track.written[0]
    assert row["kind"] == "scroll" and row["path"] == "/projects" and row["data"] == {"depth": 50}
    assert row["ip"] == "203.0.113.5" and row["city"] == "S\u00e3o Paulo"
    assert row["region"] == "SP" and row["country"] == "BR" and row["device"] == "mobile"
    assert row["network"] is None


@pytest.mark.parametrize("agent,expected", [
    ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)", "desktop"),
    ("Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X)", "tablet"),
    ("Mozilla/5.0 (Linux; Android 14; Pixel 8) Mobile Safari", "mobile"),
    ("Mozilla/5.0 (Linux; Android 14; SM-X910) Safari", "tablet"),
    ("", "desktop"),
])
def test_track_device_guess(track, agent, expected):
    assert track.device_from(agent) == expected


@pytest.mark.parametrize("kind", ["scroll", "click", "session_start", "feedback"])
def test_track_accepts_each_known_kind(dev_api, track, kind):
    assert post_track(dev_api, track, event(kind=kind))[0] == 204


def test_track_rejects_an_unknown_kind(dev_api, track):
    assert post_track(dev_api, track, event(kind="purchase"))[0] == 400
    assert track.written == []


@pytest.mark.parametrize("kind", [[], {}, ["pageview"], 5, None, True])
def test_track_rejects_a_kind_that_is_not_a_string(dev_api, track, kind):
    assert post_track(dev_api, track, event(kind=kind))[0] == 400
    assert track.written == []


def test_track_rejects_a_body_over_four_kilobytes(dev_api, track):
    assert post_track(dev_api, track, event(data={"x": "y" * 5000}))[0] == 413
    assert track.written == []


def test_track_rejects_bad_json(dev_api, track):
    assert post_track(dev_api, track, b"not json")[0] == 400


@pytest.mark.parametrize("headers", [
    [("origin", "https://evil.example")],
    [("origin", "https://portfolio-abc123-rakim.vercel.app"), ("x-forwarded-host", "portfolio-abc123-rakim.vercel.app")],
    [("origin", "https://preview.tmp.now")],
    [],
])
def test_track_refuses_everything_but_the_real_site(dev_api, track, headers):
    assert post_track(dev_api, track, event(), headers=headers)[0] == 403
    assert track.written == []


def test_track_allows_a_configured_local_host(dev_api, track, monkeypatch):
    monkeypatch.setenv("SITE_ALLOWED_ORIGINS", "http://localhost:5173")
    assert post_track(dev_api, track, event(), headers=[("origin", "http://localhost:5173")])[0] == 204


@pytest.mark.parametrize("kind,data,expected", [
    ("scroll", {"depth": 75, "extra": "x" * 300}, {"depth": 75}),
    ("scroll", {"depth": "75"}, {}),
    ("scroll", {"depth": True}, {}),
    ("scroll", {"depth": 500}, {}),
    ("feedback", {"value": "up", "other": 1}, {"value": "up"}),
    ("feedback", {"value": "sideways"}, {}),
    ("click", {"tag": "a", "text": "t" * 200, "href": "/projects", "x": "y"}, {"tag": "a", "text": "t" * 80, "href": "/projects"}),
    ("pageview", {"anything": "at all"}, {}),
    ("session_start", {"anything": "at all"}, {}),
    ("click", "not a dict", {}),
])
def test_track_keeps_only_the_expected_fields(track, kind, data, expected):
    assert track.clean_data(kind, data) == expected


def test_track_caps_data_at_one_kilobyte(track):
    big = {"tag": "\U0001f600" * 16, "text": "\U0001f600" * 80, "href": "\U0001f600" * 256}
    assert track.clean_data("click", big) == {}


def test_track_cleans_text_the_database_would_refuse(track):
    row = track.build_row({"kind": "click", "visitor_id": "v\u0000", "session_id": "s\ud800", "path": "/x\x1b[2J", "data": {"text": "a\u0000b"}}, {})
    assert row["visitor_id"] == "v" and row["session_id"] == "s" and row["path"] == "/x[2J"
    assert row["data"] == {"text": "ab"}


def test_track_rejects_deep_nesting(dev_api, track):
    assert post_track(dev_api, track, b"[" * 4000)[0] == 400


class FakeConn:
    def __init__(self, allowed=True):
        self.allowed = allowed
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
        return (self.allowed,)


@pytest.fixture
def real_write(monkeypatch):
    """track.py with its real write_event and a fake database connection."""
    import psycopg

    module = load_module(ROOT / "frontend" / "api" / "track.py", "site_track_real_write")
    conn = FakeConn()
    monkeypatch.setattr(psycopg, "connect", lambda *args, **kwargs: conn)
    monkeypatch.setenv("SITE_LOGGER_URL", "postgres://example.test/db")
    for name in ("SITE_EVENTS_PER_VISITOR_DAILY", "SITE_EVENTS_GLOBAL_DAILY", "IPINFO_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    return module, conn


def row_for(module, kind="pageview", ip="203.0.113.5"):
    return module.build_row({"kind": kind, "path": "/"}, {"x-forwarded-for": ip})


def test_an_event_takes_a_slot_then_inserts(real_write):
    module, conn = real_write
    assert module.write_event(row_for(module)) is True
    assert conn.statements[0][0].startswith("select site.take_event_slot")
    assert conn.statements[0][1] == ("203.0.113.5", 300, 20000)
    assert conn.statements[1][0].startswith("insert into site.events")
    assert conn.prepare_threshold is None


def test_an_event_over_the_limit_is_dropped(real_write):
    module, conn = real_write
    conn.allowed = False
    assert module.write_event(row_for(module)) is False
    assert len(conn.statements) == 1


def test_an_event_over_the_limit_still_answers_204(dev_api, real_write, monkeypatch):
    module, conn = real_write
    conn.allowed = False
    assert post_track(dev_api, module, event())[0] == 204
    assert len(conn.statements) == 1


def test_event_limits_group_ipv6_and_read_the_environment(real_write, monkeypatch):
    module, conn = real_write
    monkeypatch.setenv("SITE_EVENTS_PER_VISITOR_DAILY", "7")
    monkeypatch.setenv("SITE_EVENTS_GLOBAL_DAILY", "9")
    module.write_event(row_for(module, ip="2001:db8:1:2:aaaa:bbbb:cccc:dddd"))
    assert conn.statements[0][1] == ("2001:db8:1:2::/64", 7, 9)


def test_network_lookup_runs_only_for_the_start_of_a_session(real_write, monkeypatch):
    module, conn = real_write
    calls = []
    monkeypatch.setattr(module, "network_owner", lambda ip: calls.append(ip) or "Example Net")
    module.write_event(row_for(module, kind="pageview"))
    assert calls == []
    row = row_for(module, kind="session_start")
    module.write_event(row)
    assert calls == ["203.0.113.5"] and row["network"] == "Example Net"


def test_network_lookup_is_skipped_over_the_limit(real_write, monkeypatch):
    module, conn = real_write
    conn.allowed = False
    calls = []
    monkeypatch.setattr(module, "network_owner", lambda ip: calls.append(ip))
    module.write_event(row_for(module, kind="session_start"))
    assert calls == []


# ------------------------------------------------------------ database grants and the report

def schema_text():
    return (ROOT / "db" / "site_schema.sql").read_text(encoding="utf-8")


@pytest.fixture
def site_setup():
    return load_module(ROOT / "scripts" / "site_setup.py", "site_setup_for_tests")


def test_each_function_is_granted_to_its_one_role(site_setup):
    schema = schema_text()
    for function, role in site_setup.FUNCTIONS.items():
        assert f"grant execute on function {function} to {role};" in schema, function
        assert f"revoke execute on function {function} from public;" in schema, function
    assert schema.count("grant execute on function") == len(site_setup.FUNCTIONS)


def test_new_functions_are_definers_with_a_fixed_search_path():
    schema = schema_text()
    for name in ("spend_open", "month_spend_open", "record_spend", "reserve_spend", "settle_spend", "take_log_slot", "take_event_slot"):
        body = schema[schema.index(f"create or replace function site.{name}("):]
        body = body[:body.index("$$;")]
        assert "security definer" in body and "set search_path = site, public, pg_temp" in body, name


def function_body(name):
    schema = schema_text()
    body = schema[schema.index(f"create or replace function site.{name}("):]
    return body[:body.index("$$;")]


def test_the_reservation_is_one_atomic_step_against_both_ceilings():
    body = function_body("reserve_spend")
    assert "returns date" in body
    assert "day_n + units > day_limit or month_n + units > month_limit" in body
    assert body.index("on conflict (day, key) do update set n = q.n") < body.index("sum(q.n)") < body.index("set n = q.n + units")
    assert "date_trunc('month', today)" in body


def test_settling_can_give_back_but_is_limited_to_a_recent_hold():
    body = function_body("settle_spend")
    assert "settle_spend.actual" in body and "settle_spend.reserved" in body
    assert "q.day = settle_spend.reserved_on" in body
    assert "- 1" in body and "greatest(q.n +" in body


@pytest.mark.parametrize("function", ["site.reserve_spend(int, int, int)", "site.settle_spend(date, int, int)"])
def test_the_verifier_covers_the_reservation_functions(site_setup, function):
    assert site_setup.FUNCTIONS[function] == "site_search"


def test_the_verifier_flags_a_wrong_role(site_setup):
    answers = {}

    class Conn:
        def execute(self, sql, params):
            if "rolcanlogin" in sql:
                return Result((True,))
            if "has_table_privilege" in sql:
                role, table, privilege = params
                return Result(((role, table.split(".")[1], privilege) in site_setup.ALLOWED,))
            role, function = params
            answers[(role, function)] = True
            return Result((role == "site_search",))

    class Result:
        def __init__(self, row):
            self.row = row

        def fetchone(self):
            return self.row

    problems = site_setup.verify(Conn())
    assert problems == [
        "site_search: unexpected execute state on site.take_event_slot(text, int, int)",
        "site_logger: unexpected execute state on site.take_event_slot(text, int, int)",
    ]
    assert len(answers) == len(site_setup.FUNCTIONS) * 4


def test_the_report_never_prints_control_codes(capsys):
    report = load_module(ROOT / "scripts" / "site_report.py", "site_report_for_tests")
    report.table("T", ("a",), [("x\x1b[2Jy",)])
    assert "\x1b" not in capsys.readouterr().out


def test_track_drops_a_malformed_turn_id(dev_api, track):
    post_track(dev_api, track, event(kind="feedback", turn_id="not-a-uuid"))
    assert track.written[0]["turn_id"] is None
    good = "12345678-1234-5678-1234-567812345678"
    post_track(dev_api, track, event(kind="feedback", turn_id=good))
    assert track.written[1]["turn_id"] == good


def test_track_write_failure_still_answers(dev_api, track, monkeypatch):
    def broken(row):
        raise RuntimeError("database is down")

    monkeypatch.setattr(track, "write_event", broken)
    assert post_track(dev_api, track, event())[0] == 204


def test_env_file_parsing(dev_api, tmp_path):
    env = tmp_path / "local.env"
    env.write_text('# comment\nexport A_KEY=abc\nB_KEY="quoted value"\nC_KEY=has=equals\n\nnot a pair\n')
    assert dev_api.parse_env_file(env) == {"A_KEY": "abc", "B_KEY": "quoted value", "C_KEY": "has=equals"}


def test_router_sends_each_path_to_the_right_place(dev_api, track, deps, chat):
    deps.script(model_turn(["He built a desktop automation engine for this."]))
    router = dev_api.make_router(chat.app, {"/api/track": track.handler})
    assert call_app(router, path="/api/chat", headers=same_origin_headers(), body=chat_body())[0] == 200
    headers = same_origin_headers((b"content-length", str(len(event())).encode()))
    assert call_app(router, path="/api/track", headers=headers, body=event())[0] == 204
    assert track.written
    assert call_app(router, path="/api/other", headers=same_origin_headers())[0] == 404
