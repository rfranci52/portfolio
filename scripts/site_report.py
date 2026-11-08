#!/usr/bin/env python3
"""Prints a local summary of chat and visit activity.

Reads with the read-only reporting role. Output stays in the terminal and shows
visitor questions and approximate locations, so it is not meant to be shared.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from site_common import connect, fail, read_env  # noqa: E402

VISITS = """
    select visitor_id, session_id, ip, created_at, referrer, city, region, country, network
      from site.chat_log where created_at >= now() - make_interval(days => %(days)s)
    union all
    select visitor_id, session_id, ip, created_at, referrer, city, region, country, network
      from site.events where created_at >= now() - make_interval(days => %(days)s)
"""
TURNS = "from site.chat_log where created_at >= now() - make_interval(days => %(days)s)"


def printable(value: object) -> str:
    """Stored text came from visitors, so it never reaches the terminal as control codes."""
    return "".join(ch if ch.isprintable() else "?" for ch in str(value))


def table(title: str, headers: tuple[str, ...], rows: list[tuple]) -> None:
    print(f"\n{title}")
    if not rows:
        print("  (none)")
        return
    text = [tuple("" if v is None else printable(v) for v in row) for row in rows]
    widths = [max(len(h), *(len(r[i]) for r in text)) for i, h in enumerate(headers)]
    print("  " + "  ".join(h.ljust(w) for h, w in zip(headers, widths)))
    for row in text:
        print("  " + "  ".join(v.ljust(w) for v, w in zip(row, widths)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--days", type=int, default=30, help="how far back to look")
    parser.add_argument("--top", type=int, default=20, help="rows per list")
    args = parser.parse_args()

    url = read_env().get("SITE_READER_URL", "")
    if not url:
        fail("SITE_READER_URL is not set; run scripts/site_setup.py first")
    params = {"days": args.days, "top": args.top}

    conn = connect(url)

    def rows(query: str) -> list[tuple]:
        return conn.execute(query, params).fetchall()

    try:
        print(f"Last {args.days} days")

        table(
            "Visitors",
            ("visitors", "sessions", "ip addresses"),
            rows(f"""
                select count(distinct visitor_id), count(distinct session_id), count(distinct ip)
                from ({VISITS}) v
            """),
        )
        table(
            "Repeat visits",
            ("visitor", "sessions", "days", "first seen", "last seen"),
            rows(f"""
                select left(visitor_id, 12), count(distinct session_id), count(distinct created_at::date),
                       min(created_at)::date, max(created_at)::date
                from ({VISITS}) v
                where visitor_id is not null
                group by visitor_id
                having count(distinct session_id) > 1
                order by 2 desc, 3 desc
                limit %(top)s
            """),
        )
        table(
            "Top questions",
            ("count", "question"),
            rows(f"""
                select count(*), left(lower(trim(question)), 90)
                {TURNS}
                group by 2
                order by 1 desc, 2
                limit %(top)s
            """),
        )
        table(
            "Referrers",
            ("visitors", "referrer"),
            rows(f"""
                select count(distinct visitor_id), coalesce(nullif(referrer, ''), '(direct)')
                from ({VISITS}) v
                group by 2
                order by 1 desc, 2
                limit %(top)s
            """),
        )
        table(
            "Cities",
            ("visitors", "city", "region", "country"),
            rows(f"""
                select count(distinct visitor_id), city, region, country
                from ({VISITS}) v
                where city is not null
                group by 2, 3, 4
                order by 1 desc, 2
                limit %(top)s
            """),
        )
        table(
            "Networks",
            ("visitors", "network"),
            rows(f"""
                select count(distinct visitor_id), network
                from ({VISITS}) v
                where network is not null and network <> ''
                group by 2
                order by 1 desc, 2
                limit %(top)s
            """),
        )
        table(
            "Cost",
            ("model", "turns", "cost usd", "avg usd", "input", "output", "cache read",
             "web searches", "avg ms first token", "avg ms total"),
            rows(f"""
                select coalesce(model, '(none)'), count(*), coalesce(sum(cost_usd), 0),
                       round(avg(cost_usd), 5), coalesce(sum(input_tokens), 0),
                       coalesce(sum(output_tokens), 0), coalesce(sum(cache_read_tokens), 0),
                       coalesce(sum(web_searches), 0), round(avg(ms_first_token)), round(avg(ms_total))
                {TURNS}
                group by 1
                order by 3 desc
            """),
        )
        table(
            "Outcomes",
            ("count", "outcome"),
            rows(f"""
                select count(*), coalesce(outcome, '(none)')
                {TURNS}
                group by 2
                order by 1 desc, 2
            """),
        )
        table(
            "Refusals and screen flags",
            ("count", "flag"),
            rows(f"""
                select count(*), flag
                from (select unnest(flags) as flag {TURNS}) f
                group by 2
                order by 1 desc, 2
            """),
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
