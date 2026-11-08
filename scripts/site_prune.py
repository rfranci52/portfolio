#!/usr/bin/env python3
"""Removes old rows from the site's log tables and daily counters.

Runs locally with NEON_OWNER_URL, the only role with the right to remove rows. The
roles the deployed functions use cannot. Prints counts only. Nothing runs this on a
schedule, and --days has no default, so rows are removed only when someone asks.

    python scripts/site_prune.py --days N
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from site_common import connect, fail, read_env  # noqa: E402

COUNTER_DAYS = 7


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--days", type=int, required=True, help="remove chat and visit rows older than this many days")
    args = parser.parse_args()
    if args.days < 1:
        fail("--days must be at least 1")

    owner_url = read_env().get("NEON_OWNER_URL", "")
    if not owner_url:
        fail("NEON_OWNER_URL is empty")
    conn = connect(owner_url)
    try:
        with conn.transaction():
            for table in ("chat_log", "events"):
                removed = conn.execute(
                    f"delete from site.{table} where created_at < now() - make_interval(days => %s)",
                    (args.days,),
                ).rowcount
                print(f"{table}: removed {removed}")
            removed = conn.execute(
                "delete from site.quota where day < (now() at time zone 'utc')::date - %s::int",
                (COUNTER_DAYS,),
            ).rowcount
            print(f"quota: removed {removed}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
