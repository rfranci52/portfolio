#!/usr/bin/env python3
"""Builds the retrieval index from content/*.md and content/projects/*.md.

Every chunk is checked against the privacy screen first. Any hit exits non-zero
and writes nothing, reporting only the chunk id and the kind of term. Unchanged
chunks are not embedded again, and chunks that no longer exist are deleted.
--offline checks chunking and the screen against a local terms file, with no
database and no embedding calls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import secrets
import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from site_common import (  # noqa: E402
    PRIVATE_DIR,
    REPO_ROOT,
    Keys,
    ScreenTerm,
    connect,
    fail,
    parse_terms,
    read_env,
    screen_hits,
)

CONTENT_DIR = REPO_ROOT / "content"
WORD_LIMIT = 300
VOYAGE_URL = "https://api.voyageai.com/v1/embeddings"
VOYAGE_MODEL = "voyage-4-large"
EMBED_DIMENSIONS = 1024
EMBED_BATCH = 64
# About 7,500 tokens, so a single batch fits inside a low per-minute token limit.
EMBED_BATCH_CHARS = 30_000


@dataclass(frozen=True)
class Chunk:
    id: str
    doc: str
    title: str
    section: str
    url: str
    content: str

    @property
    def embed_text(self) -> str:
        return f"{self.title} / {self.section}\n\n{self.content}"

    @property
    def sha(self) -> str:
        return hashlib.sha256(self.embed_text.encode("utf-8")).hexdigest()


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "section"


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    for index, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            meta: dict[str, str] = {}
            for entry in lines[1:index]:
                if ":" in entry:
                    key, value = entry.split(":", 1)
                    meta[key.strip()] = value.strip().strip("\"'")
            return meta, "\n".join(lines[index + 1:])
    return {}, text


def split_sections(body: str) -> list[tuple[str, str]]:
    """Splits on '## ' headings. Text before the first heading becomes Overview."""
    sections: list[tuple[str, list[str]]] = [("Overview", [])]
    fenced = False
    for line in body.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        if not fenced and line.startswith("## "):
            sections.append((line[3:].strip(), []))
        elif not fenced and line.startswith("# ") and len(sections) == 1:
            continue  # the page title is already in the front matter
        else:
            sections[-1][1].append(line)
    return [(name, "\n".join(lines).strip()) for name, lines in sections if "".join(lines).strip()]


def _split_paragraph(paragraph: str, limit: int) -> list[str]:
    pieces: list[str] = []
    current: list[str] = []
    count = 0
    for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
        words = sentence.split()
        while len(words) > limit:  # a single very long sentence
            if current:
                pieces.append(" ".join(current))
                current, count = [], 0
            pieces.append(" ".join(words[:limit]))
            words = words[limit:]
        if count and count + len(words) > limit:
            pieces.append(" ".join(current))
            current, count = [], 0
        current.extend(words)
        count += len(words)
    if current:
        pieces.append(" ".join(current))
    return pieces


def split_long(text: str, limit: int = WORD_LIMIT) -> list[str]:
    """Keeps a section whole unless it runs past the limit, then splits on paragraphs."""
    if len(text.split()) <= limit:
        return [text]
    parts: list[str] = []
    current: list[str] = []
    count = 0

    def flush() -> None:
        nonlocal current, count
        if current:
            parts.append("\n\n".join(current))
            current, count = [], 0

    for paragraph in re.split(r"\n\s*\n", text):
        words = len(paragraph.split())
        if words > limit:
            flush()
            parts.extend(_split_paragraph(paragraph, limit))
        else:
            if count and count + words > limit:
                flush()
            current.append(paragraph.strip())
            count += words
    flush()
    return parts


def load_document(path: Path, seen_docs: set[str]) -> list[Chunk]:
    doc = path.stem
    relative = path.relative_to(REPO_ROOT)
    if doc in seen_docs:
        fail(f"{relative}: another document already uses this file name")
    seen_docs.add(doc)
    meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
    if not meta.get("title") or not meta.get("url"):
        fail(f"{relative}: front matter needs title and url")

    chunks: list[Chunk] = []
    used: dict[str, int] = {}
    for section, text in split_sections(body):
        slug = slugify(section)
        used[slug] = used.get(slug, 0) + 1
        if used[slug] > 1:
            slug = f"{slug}-{used[slug]}"
        parts = split_long(text)
        for number, part in enumerate(parts, 1):
            suffix = f":{number}" if len(parts) > 1 else ""
            chunks.append(
                Chunk(
                    id=f"{doc}:{slug}{suffix}",
                    doc=doc,
                    title=meta["title"],
                    section=section,
                    url=meta["url"],
                    content=part,
                )
            )
    return chunks


def load_corpus(content_dir: Path = CONTENT_DIR) -> list[Chunk]:
    seen_docs: set[str] = set()
    chunks: list[Chunk] = []
    for path in sorted(content_dir.glob("*.md")) + sorted((content_dir / "projects").glob("*.md")):
        chunks.extend(load_document(path, seen_docs))
    return chunks


def screen_corpus(chunks: list[Chunk], terms: dict[str, ScreenTerm], keys: Keys) -> bool:
    """Prints chunk id and kind for every hit. Returns True when the corpus is clean."""
    clean = True
    for chunk in chunks:
        text = f"{chunk.title}\n{chunk.section}\n{chunk.content}"
        for kind in sorted(screen_hits(text, terms, keys)):
            print(f"privacy screen hit: {chunk.id}: {kind}", file=sys.stderr)
            clean = False
    return clean


def embed_batches(texts: list[str]) -> list[list[str]]:
    """Splits texts into batches limited by both count and size."""
    batches: list[list[str]] = []
    current: list[str] = []
    size = 0
    for text in texts:
        if current and (len(current) >= EMBED_BATCH or size + len(text) > EMBED_BATCH_CHARS):
            batches.append(current)
            current, size = [], 0
        current.append(text)
        size += len(text)
    if current:
        batches.append(current)
    return batches


def embed(texts: list[str], api_key: str) -> list[str]:
    """Returns one pgvector literal per text, in order."""
    import httpx

    vectors: list[str] = []
    with httpx.Client(timeout=90) as client:
        for batch in embed_batches(texts):
            for attempt in range(7):
                response = client.post(
                    VOYAGE_URL,
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": VOYAGE_MODEL,
                        "input": batch,
                        "input_type": "document",
                        "output_dimension": EMBED_DIMENSIONS,
                    },
                )
                if response.status_code in (429, 500, 502, 503, 504) and attempt < 6:
                    # Rate limits reset each minute, so a short backoff would just fail again.
                    time.sleep(65 if response.status_code == 429 else 2 ** attempt)
                    continue
                break
            if response.status_code != 200:
                fail(f"embedding request failed with status {response.status_code}", 1)
            data = sorted(response.json()["data"], key=lambda item: item.get("index", 0))
            if len(data) != len(batch):
                fail("embedding response had the wrong number of vectors", 1)
            for item in data:
                if len(item["embedding"]) != EMBED_DIMENSIONS:
                    fail("embedding response had the wrong dimension", 1)
                vectors.append(json.dumps(item["embedding"], separators=(",", ":")))
    return vectors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--offline", action="store_true", help="no database, no embedding calls")
    parser.add_argument("--terms", type=Path, default=PRIVATE_DIR / "blocklist.txt")
    args = parser.parse_args()

    chunks = load_corpus()
    if not chunks:
        fail("no content found; refusing to empty the index")
    documents = len({c.doc for c in chunks})
    env = read_env()

    if args.offline:
        keys = Keys(env.get("SITE_HASH_PEPPER") or secrets.token_hex(32))
        parsed = parse_terms(args.terms, keys)
        if parsed.errors:
            fail(f"terms file has {len(parsed.errors)} problem(s)")
        if not screen_corpus(chunks, parsed.terms, keys):
            raise SystemExit(1)
        print(f"offline check ok: {documents} documents, {len(chunks)} chunks, privacy screen clean")
        return

    owner_url = env.get("NEON_OWNER_URL", "")
    api_key = env.get("VOYAGE_API_KEY", "")
    if not owner_url or not api_key:
        fail("NEON_OWNER_URL and VOYAGE_API_KEY must both be set")
    keys = Keys(env.get("SITE_HASH_PEPPER", ""))

    conn = connect(owner_url)
    try:
        terms = {
            row[0]: ScreenTerm(row[1], row[2])
            for row in conn.execute("select hash, kind, guarded from site.screen_terms")
        }
        if not terms:
            fail("the privacy screen is empty; run scripts/build_screen.py first")
        if not screen_corpus(chunks, terms, keys):
            raise SystemExit(1)

        existing = dict(conn.execute("select id, content_sha from site.chunks").fetchall())
        changed = [c for c in chunks if existing.get(c.id) != c.sha]
        unchanged = [c for c in chunks if existing.get(c.id) == c.sha]
        vectors = embed([c.embed_text for c in changed], api_key) if changed else []

        with conn.transaction():
            with conn.cursor() as cur:
                if changed:
                    cur.executemany(
                        """
                        insert into site.chunks
                          (id, doc, title, section, url, content, embedding, content_sha, indexed_at)
                        values (%s, %s, %s, %s, %s, %s, %s::vector, %s, now())
                        on conflict (id) do update set
                          doc = excluded.doc, title = excluded.title, section = excluded.section,
                          url = excluded.url, content = excluded.content,
                          embedding = excluded.embedding, content_sha = excluded.content_sha,
                          indexed_at = now()
                        """,
                        [
                            (c.id, c.doc, c.title, c.section, c.url, c.content, v, c.sha)
                            for c, v in zip(changed, vectors, strict=True)
                        ],
                    )
                if unchanged:
                    cur.executemany(
                        "update site.chunks set doc = %s, url = %s where id = %s",
                        [(c.doc, c.url, c.id) for c in unchanged],
                    )
                cur.execute("delete from site.chunks where id <> all(%s)", ([c.id for c in chunks],))
                deleted = cur.rowcount
    finally:
        conn.close()
    print(
        f"index built: {documents} documents, {len(chunks)} chunks, "
        f"embedded {len(changed)}, unchanged {len(unchanged)}, deleted {deleted}"
    )


if __name__ == "__main__":
    main()
