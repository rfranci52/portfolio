#!/usr/bin/env python3
"""Creates or updates the site database objects and its three login roles.

Uses NEON_OWNER_URL from the private env file. On the first run it generates the
hash pepper and the role passwords, then writes the pepper and three pooled
connection URLs back to that file. Later runs reuse them, so running this again
changes nothing. No secret is ever printed.
"""
from __future__ import annotations

import secrets
import sys
from pathlib import Path
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from site_common import ENV_FILE, REPO_ROOT, connect, fail, read_env, write_env  # noqa: E402

SCHEMA_FILE = REPO_ROOT / "db" / "site_schema.sql"
ROLES = {
    "site_search": "SITE_SEARCH_URL",
    "site_logger": "SITE_LOGGER_URL",
    "site_reader": "SITE_READER_URL",
}
TABLES = (
    "chunks", "org_context", "org_keys", "screen_terms", "config",
    "web_cache", "quota", "chat_log", "events",
)
# Each function and the one role allowed to run it.
FUNCTIONS = {
    "site.lookup_org(text[])": "site_search",
    "site.take_quota(text, int, int)": "site_search",
    "site.web_cache_get(text)": "site_search",
    "site.web_cache_put(text, text, text, text, jsonb)": "site_search",
    "site.spend_open(int)": "site_search",
    "site.month_spend_open(int)": "site_search",
    "site.record_spend(int)": "site_search",
    "site.reserve_spend(int, int, int)": "site_search",
    "site.settle_spend(date, int, int)": "site_search",
    "site.take_log_slot(text, int)": "site_search",
    "site.take_event_slot(text, int, int)": "site_logger",
}
ALLOWED = {
    ("site_search", "chunks", "select"),
    ("site_search", "screen_terms", "select"),
    ("site_search", "config", "select"),
    ("site_logger", "chat_log", "insert"),
    ("site_logger", "events", "insert"),
    ("site_reader", "chat_log", "select"),
    ("site_reader", "events", "select"),
}


def pooled_host(host: str) -> str:
    first, _, rest = host.partition(".")
    return host if first.endswith("-pooler") else f"{first}-pooler.{rest}"


def role_url(owner_url: str, role: str, password: str) -> str:
    """Builds a pooled URL for a role. Drops any startup options parameter."""
    parts = urlsplit(owner_url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != "options"]
    if not any(k == "sslmode" for k, _ in query):
        query.append(("sslmode", "require"))
    port = f":{parts.port}" if parts.port else ""
    netloc = f"{quote(role, safe='')}:{quote(password, safe='')}@{pooled_host(parts.hostname)}{port}"
    return urlunsplit((parts.scheme, netloc, parts.path, urlencode(query), ""))


def existing_password(url: str | None, role: str) -> str | None:
    if not url:
        return None
    parts = urlsplit(url)
    if parts.username == role and parts.password:
        return unquote(parts.password)
    return None


def plan(env: dict[str, str], owner_url: str) -> tuple[dict[str, str], dict[str, str]]:
    """Returns (env updates, role passwords). Reuses anything already generated."""
    updates: dict[str, str] = {}
    if not env.get("SITE_HASH_PEPPER"):
        updates["SITE_HASH_PEPPER"] = secrets.token_hex(32)
    passwords: dict[str, str] = {}
    for role, variable in ROLES.items():
        password = existing_password(env.get(variable), role) or secrets.token_urlsafe(32)
        passwords[role] = password
        url = role_url(owner_url, role, password)
        if env.get(variable) != url:
            updates[variable] = url
    return updates, passwords


def verify(conn) -> list[str]:
    """Checks the live grants against the spec. Returns one line per problem."""
    problems: list[str] = []
    for role in ROLES:
        login = conn.execute("select rolcanlogin from pg_roles where rolname = %s", (role,)).fetchone()
        if not login or not login[0]:
            problems.append(f"{role}: cannot log in")
        for table in TABLES:
            for privilege in ("select", "insert", "update", "delete"):
                has = conn.execute(
                    "select has_table_privilege(%s, %s, %s)", (role, f"site.{table}", privilege)
                ).fetchone()[0]
                if has != ((role, table, privilege) in ALLOWED):
                    problems.append(f"{role}: unexpected {privilege} state on {table}")
    for function, grantee in FUNCTIONS.items():
        for role in ("public", *ROLES):
            has = conn.execute(
                "select has_function_privilege(%s, %s, 'execute')", (role, function)
            ).fetchone()[0]
            if has != (role == grantee):
                problems.append(f"{role}: unexpected execute state on {function}")
    return problems


def main() -> None:
    import psycopg
    from psycopg import sql

    env = read_env()
    owner_url = env.get("NEON_OWNER_URL", "")
    if not owner_url:
        fail(f"NEON_OWNER_URL is empty in {ENV_FILE.name}")
    parts = urlsplit(owner_url)
    if parts.scheme not in ("postgres", "postgresql") or not parts.hostname:
        fail("NEON_OWNER_URL is not a postgres connection URL")
    if not SCHEMA_FILE.exists():
        fail("db/site_schema.sql was not found")

    updates, passwords = plan(env, owner_url)
    # Written before the database work so a failed run reuses the same values.
    if updates:
        write_env(updates)

    conn = connect(owner_url)
    try:
        with conn.transaction():
            conn.execute(SCHEMA_FILE.read_text(encoding="utf-8"))
            for role, password in passwords.items():
                conn.execute(
                    sql.SQL("alter role {} login password {}").format(
                        sql.Identifier(role), sql.Literal(password)
                    )
                )
        problems = verify(conn)
    except psycopg.Error as exc:
        fail(f"database step failed ({type(exc).__name__}, sqlstate {exc.sqlstate})")
    finally:
        conn.close()

    if problems:
        for line in problems:
            print(f"grant check: {line}", file=sys.stderr)
        raise SystemExit(1)
    print(f"schema ok, {len(ROLES)} roles ok, grants verified, {len(updates)} env values written")


if __name__ == "__main__":
    main()
