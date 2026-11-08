#!/usr/bin/env python3
"""Loads the privacy screen and the private policy text into the database.

Terms are stored only as salted hashes. Output is counts by kind; a bad line is
reported by line number. --check parses the files without touching the database.
A list of made-up organization names is also created once and then kept, because
the keyed choice from it should stay stable.
"""
from __future__ import annotations

import argparse
import json
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from site_common import PRIVATE_DIR, Keys, connect, fail, parse_terms, read_env, screen_hits  # noqa: E402

# Hashes owned by scripts/import_org_context.py. They are kept here on purpose.
ORG_SCREEN_KEY = "org_screen_hashes"

DECOY_KEY = "org_decoys"
DECOY_COUNT = 64
DECOY_WORDS = (
    (
        "Alder", "Bracken", "Cinder", "Dunmore", "Elmhurst", "Fenwick", "Garnet", "Hollis", "Ironwood",
        "Juniper", "Kestrel", "Larchmont", "Merrow", "Northfield", "Oakhaven", "Pinecrest", "Quarry",
        "Redfern", "Stonebridge", "Thornton", "Umber", "Vantor", "Westbrook", "Yarrow",
    ),
    (
        "Analytics", "Bio", "Data", "Energy", "Foods", "Freight", "Health", "Industries", "Logistics",
        "Media", "Mobility", "Networks", "Retail", "Robotics", "Software", "Systems", "Therapeutics",
    ),
    ("Group", "Inc", "Labs", "Partners", "Holdings"),
)


def make_decoys(terms, keys) -> list[str]:
    """Random made-up organization names, none of which trip the privacy screen."""
    chosen: set[str] = set()
    while len(chosen) < DECOY_COUNT:
        name = " ".join(secrets.choice(words) for words in DECOY_WORDS)
        if not screen_hits(name, terms, keys, kinds=("name", "self", "deflect", "say")):
            chosen.add(name)
    return sorted(chosen)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--terms", type=Path, default=PRIVATE_DIR / "blocklist.txt")
    parser.add_argument("--addendum", type=Path, default=PRIVATE_DIR / "policy_addendum.md")
    parser.add_argument("--check", action="store_true", help="parse only, no database")
    args = parser.parse_args()

    env = read_env()
    pepper = env.get("SITE_HASH_PEPPER", "")
    if args.check and not pepper:
        pepper = secrets.token_hex(32)  # hashes are only compared within this run
    keys = Keys(pepper)

    parsed = parse_terms(args.terms, keys)
    if parsed.errors:
        for line in parsed.errors:
            print(f"terms file: {line}", file=sys.stderr)
        raise SystemExit(1)
    if not parsed.terms:
        fail("the terms file has no entries")
    if not args.addendum.exists() or not args.addendum.read_text(encoding="utf-8").strip():
        fail("the policy text file is missing or empty")
    addendum = args.addendum.read_text(encoding="utf-8").strip()

    summary = ", ".join(f"{kind} {count}" for kind, count in parsed.counts().items())
    decoys = make_decoys(parsed.terms, keys)
    if args.check:
        print(f"check ok (no database): {summary}, merged duplicates {parsed.merged}, decoys {len(decoys)}")
        return

    owner_url = env.get("NEON_OWNER_URL", "")
    if not owner_url:
        fail("NEON_OWNER_URL is empty")
    conn = connect(owner_url)
    try:
        with conn.transaction():
            row = conn.execute(
                "select value from site.config where key = %s", (ORG_SCREEN_KEY,)
            ).fetchone()
            keep = list(parsed.terms) + (json.loads(row[0]) if row else [])
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    insert into site.screen_terms (hash, kind, guarded) values (%s, %s, %s)
                    on conflict (hash) do update
                      set kind = excluded.kind, guarded = excluded.guarded
                    """,
                    [(h, t.kind, t.guarded) for h, t in parsed.terms.items()],
                )
                cur.execute("delete from site.screen_terms where hash <> all(%s)", (keep,))
                removed = cur.rowcount
            conn.execute(
                """
                insert into site.config (key, value) values ('policy_addendum', %s)
                on conflict (key) do update set value = excluded.value
                """,
                (addendum,),
            )
            conn.execute(
                "insert into site.config (key, value) values (%s, %s) on conflict (key) do nothing",
                (DECOY_KEY, json.dumps(decoys)),
            )
    finally:
        conn.close()
    print(f"privacy screen loaded: {summary}, removed {removed}, policy text updated")


if __name__ == "__main__":
    main()
