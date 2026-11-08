#!/usr/bin/env python3
"""Loads organization context, or removes all of it with --purge.

Each load replaces what was there. Names are stored only as salted hashes in
org_keys. A fact field that trips the privacy screen is left blank. --check parses
the input without touching the database. Output is counts.
"""
from __future__ import annotations

import argparse
import csv
import json
import secrets
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from site_common import (  # noqa: E402
    MAX_TOKENS,
    PRIVATE_DIR,
    Keys,
    ScreenTerm,
    connect,
    fail,
    is_guarded,
    parse_terms,
    read_env,
    screen_hits,
)

ORG_SCREEN_KEY = "org_screen_hashes"
REQUIRED_COLUMNS = {
    "company", "aliases", "common_word", "what_they_do", "team_focus", "closest_work", "exclude",
}


@dataclass
class Org:
    display_name: str
    what_they_do: str | None
    team_focus: str | None
    closest_work: list[str]
    keys: list[tuple[str, bool]]  # (hash, guarded)


@dataclass
class Parsed:
    orgs: list[Org] = field(default_factory=list)
    screened: dict[str, bool] = field(default_factory=dict)  # hash -> guarded
    rows: int = 0
    skipped_rows: int = 0
    duplicate_keys: int = 0
    unusable_keys: int = 0
    blanked_fields: int = 0


def is_yes(value: str | None) -> bool:
    return (value or "").strip().lower() == "yes"


def clean(value: str | None) -> str | None:
    """Empty fields stay empty."""
    text = (value or "").strip()
    return text or None


def split_list(value: str | None, separator: str) -> list[str]:
    return [part.strip() for part in (value or "").split(separator) if part.strip()]


def names_for(row: dict[str, str]) -> list[str]:
    return [row.get("company") or ""] + split_list(row.get("aliases"), ";")


def screened_fact(value: str | None, terms: dict[str, ScreenTerm], keys: Keys, parsed: Parsed) -> str | None:
    """A fact field, or None when it trips the privacy screen."""
    text = clean(value)
    if text is not None and screen_hits(text, terms, keys, kinds=("name", "deflect", "say")):
        parsed.blanked_fields += 1
        return None
    return text


def parse_source(path: Path, keys: Keys, terms: dict[str, ScreenTerm]) -> Parsed:
    parsed = Parsed()
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            fail(f"the input is missing {len(missing)} required column(s)")
        rows = list(reader)

    parsed.rows = len(rows)
    taken: set[str] = set()
    for row in rows:
        common = is_yes(row.get("common_word"))
        hashed: dict[str, bool] = {}
        for name in names_for(row):
            norm = keys.normalize(name)
            if not norm or len(norm.split()) > MAX_TOKENS:
                parsed.unusable_keys += 1
                continue
            for form in keys.forms(norm):
                hashed.setdefault(keys.hash(form), is_guarded(common, norm))

        if is_yes(row.get("exclude")):
            parsed.skipped_rows += 1
            parsed.screened.update(hashed)
            continue

        display_name = clean(row.get("company"))
        if display_name is None:
            parsed.unusable_keys += 1
            continue
        org_keys: list[tuple[str, bool]] = []
        for key_hash, guarded in hashed.items():
            if key_hash in taken:
                parsed.duplicate_keys += 1
                continue
            taken.add(key_hash)
            org_keys.append((key_hash, guarded))
        parsed.orgs.append(
            Org(
                display_name=display_name,
                what_they_do=screened_fact(row.get("what_they_do"), terms, keys, parsed),
                team_focus=screened_fact(row.get("team_focus"), terms, keys, parsed),
                closest_work=split_list(row.get("closest_work"), ","),
                keys=org_keys,
            )
        )
    return parsed


def owned_screen_hashes(conn) -> list[str]:
    row = conn.execute("select value from site.config where key = %s", (ORG_SCREEN_KEY,)).fetchone()
    return json.loads(row[0]) if row else []


def purge(conn) -> None:
    with conn.transaction():
        owned = owned_screen_hashes(conn)
        with conn.cursor() as cur:
            cur.execute("delete from site.org_context")
            organizations = cur.rowcount
            cur.execute("delete from site.org_keys")
            cur.execute("delete from site.screen_terms where hash = any(%s)", (owned,))
            screened = cur.rowcount
            cur.execute("delete from site.config where key = %s", (ORG_SCREEN_KEY,))
    print(f"organization context removed: organizations {organizations}, screened names {screened}")


def load(conn, parsed: Parsed) -> None:
    with conn.transaction():
        previous = owned_screen_hashes(conn)
        with conn.cursor() as cur:
            cur.execute("delete from site.org_context")
            cur.execute("delete from site.org_keys")
            for org in parsed.orgs:
                cur.execute(
                    """
                    insert into site.org_context (display_name, what_they_do, team_focus, closest_work)
                    values (%s, %s, %s, %s) returning org_id
                    """,
                    (org.display_name, org.what_they_do, org.team_focus, org.closest_work),
                )
                org_id = cur.fetchone()[0]
                if org.keys:
                    cur.executemany(
                        "insert into site.org_keys (key_hash, org_id, guarded) values (%s, %s, %s)",
                        [(key_hash, org_id, guarded) for key_hash, guarded in org.keys],
                    )

            stale = [h for h in previous if h not in parsed.screened]
            cur.execute("delete from site.screen_terms where hash = any(%s)", (stale,))

            # A hash the privacy screen already has belongs to it and is left alone.
            owned = [h for h in previous if h in parsed.screened]
            for key_hash, guarded in parsed.screened.items():
                cur.execute(
                    """
                    insert into site.screen_terms (hash, kind, guarded) values (%s, 'name', %s)
                    on conflict (hash) do nothing returning hash
                    """,
                    (key_hash, guarded),
                )
                if cur.fetchone():
                    owned.append(key_hash)

            cur.execute(
                """
                insert into site.config (key, value) values (%s, %s)
                on conflict (key) do update set value = excluded.value
                """,
                (ORG_SCREEN_KEY, json.dumps(sorted(set(owned)))),
            )
            cur.execute(
                """
                select count(*) from site.org_keys k
                join site.screen_terms s on s.hash = k.key_hash
                where s.kind = 'name'
                """
            )
            overlap = cur.fetchone()[0]
    print(f"{summarize(parsed)}, keys overlapping the privacy screen {overlap}")


def summarize(parsed: Parsed) -> str:
    keys = [k for org in parsed.orgs for k in org.keys]
    return (
        f"rows {parsed.rows}, organizations {len(parsed.orgs)}, keys {len(keys)}, "
        f"guarded keys {sum(1 for _, guarded in keys if guarded)}, "
        f"screened rows {parsed.skipped_rows}, duplicate keys {parsed.duplicate_keys}, "
        f"unusable keys {parsed.unusable_keys}, blanked fields {parsed.blanked_fields}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--source", type=Path, metavar="PATH", help="local file to load")
    action.add_argument("--purge", action="store_true", help="delete all organization context")
    parser.add_argument("--terms", type=Path, default=PRIVATE_DIR / "blocklist.txt")
    parser.add_argument("--check", action="store_true", help="parse only, no database")
    args = parser.parse_args()
    if args.check and args.purge:
        fail("--check only works with --source")

    env = read_env()
    if args.purge:
        conn = connect(env.get("NEON_OWNER_URL") or fail("NEON_OWNER_URL is empty"))
        try:
            purge(conn)
        finally:
            conn.close()
        return

    if not args.source.exists():
        fail("the input file was not found")
    pepper = env.get("SITE_HASH_PEPPER", "")
    if args.check and not pepper:
        pepper = secrets.token_hex(32)  # hashes are only compared within this run
    keys = Keys(pepper)
    screen = parse_terms(args.terms, keys)
    if screen.errors or not screen.terms:
        fail("the privacy screen terms could not be read")
    parsed = parse_source(args.source, keys, screen.terms)
    if args.check:
        print(f"check ok (no database): {summarize(parsed)}")
        return

    conn = connect(env.get("NEON_OWNER_URL") or fail("NEON_OWNER_URL is empty"))
    try:
        load(conn, parsed)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
