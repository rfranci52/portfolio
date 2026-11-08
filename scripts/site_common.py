"""Shared helpers for the local site maintenance scripts.

None of this runs on the deployed site. Secrets come from an env file outside
the repo and are never printed. Text normalizing and hashing come from
frontend/api/chat.py so there is exactly one implementation.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import NoReturn

REPO_ROOT = Path(__file__).resolve().parents[1]


def _private_dir() -> Path:
    """The folder outside the repo with the env file and the screen inputs.

    Its location is specific to one machine, so it comes from SITE_SECRETS_DIR or
    from the gitignored file .claude/secrets_dir.
    """
    value = os.environ.get("SITE_SECRETS_DIR", "").strip()
    pointer = REPO_ROOT / ".claude" / "secrets_dir"
    if not value and pointer.exists():
        value = pointer.read_text(encoding="utf-8").strip()
    return Path(value) if value else REPO_ROOT / ".claude" / "secrets"


PRIVATE_DIR = _private_dir()
ENV_FILE = PRIVATE_DIR / ".env.site"
CHAT_MODULE = REPO_ROOT / "frontend" / "api" / "chat.py"

# Strongest first. Name terms are screened everywhere, deflect terms in visitor
# text and answers, say terms in answers only, self terms only in lookups.
KINDS = ("name", "deflect", "say", "self")
MAX_TOKENS = 5  # longer phrases can never match, since n-grams stop at 5 tokens


def fail(message: str, code: int = 2) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def read_env(path: Path = ENV_FILE) -> dict[str, str]:
    """Parses KEY=VALUE lines. Values are data; nothing here goes near a shell."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def write_env(updates: dict[str, str], path: Path = ENV_FILE) -> None:
    """Replaces or appends keys, keeps every other line, and leaves the file 0600."""
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    remaining = dict(updates)
    output: list[str] = []
    for line in lines:
        key = line.split("=", 1)[0].strip().removeprefix("export ").strip() if "=" in line else ""
        if key in remaining and not line.lstrip().startswith("#"):
            output.append(f"{key}={remaining.pop(key)}")
        else:
            output.append(line)
    output.extend(f"{key}={value}" for key, value in remaining.items())

    handle, temp_name = tempfile.mkstemp(dir=path.parent, prefix=".env.site.")
    try:
        os.fchmod(handle, 0o600)
        with os.fdopen(handle, "w", encoding="utf-8") as temp:
            temp.write("\n".join(output) + "\n")
        os.replace(temp_name, path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise


def connect(url: str):
    """Opens an autocommit connection that is safe on a pooled URL."""
    import psycopg

    try:
        conn = psycopg.connect(url, autocommit=True, connect_timeout=15)
    except psycopg.Error as exc:
        fail(f"could not connect to the database ({type(exc).__name__})")
    conn.prepare_threshold = None
    return conn


def _load_chat():
    if not CHAT_MODULE.exists():
        fail("frontend/api/chat.py was not found; it holds normalize, ngrams and hash_key")
    spec = importlib.util.spec_from_file_location("site_chat_module", CHAT_MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in ("normalize", "ngrams", "hash_key", "key_forms", "scan_text"):
        if not callable(getattr(module, name, None)):
            fail(f"frontend/api/chat.py does not define {name}")
    return module


class Keys:
    """Normalizing, n-grams, peppered hashes and the guard rule, all from chat.py."""

    def __init__(self, pepper: str):
        if not pepper:
            fail("SITE_HASH_PEPPER is not set; run scripts/site_setup.py first")
        self.pepper = pepper
        self._chat = _load_chat()
        self._check_contract()

    def normalize(self, text: str) -> str:
        return self._chat.normalize(text)

    def hash(self, text: str) -> str:
        return self._chat.hash_key(text, self.pepper)

    def forms(self, term: str) -> list[str]:
        """The stored forms of one term: as written, and with its spaces taken out."""
        return self._chat.key_forms(term)

    def scan(self, text: str, terms: dict[str, "ScreenTerm"], kinds: tuple[str, ...]) -> set[str]:
        """The kinds of term found in the text, by the same matcher the site uses."""
        table = {key: {"kind": term.kind, "guarded": term.guarded} for key, term in terms.items()}
        return {hit[2] for hit in self._chat.scan_text(text, kinds, table, self.pepper)}

    def _check_contract(self) -> None:
        """A silent hash mismatch would leave the screen matching nothing."""
        for raw, folded in (
            ("  Alpha & Beta-Gamma ", "alpha beta gamma"),
            ("Ca\u0301fe\u200b \uff21lpha", "cafe alpha"),
            ("\u0430lpha", "alpha"),
        ):
            if self.normalize(raw) != folded:
                fail("normalize in chat.py does not match the documented behavior")
        expected = hashlib.sha256(f"{self.pepper}|alpha beta".encode("utf-8")).hexdigest()
        if self.hash("Alpha Beta") != expected:
            fail("hash_key in chat.py does not match the documented behavior")
        if self.forms("Alpha Beta") != ["alpha beta", "alphabeta"] or self.forms("Alpha") != ["alpha"]:
            fail("key_forms in chat.py does not match the documented behavior")


@dataclass(frozen=True)
class ScreenTerm:
    kind: str
    guarded: bool
    alias: bool = False  # the space-free form of another term


@dataclass
class ParsedTerms:
    terms: dict[str, ScreenTerm] = field(default_factory=dict)  # hash -> term
    errors: list[str] = field(default_factory=list)  # line numbers and reasons only
    merged: int = 0

    def counts(self) -> dict[str, int]:
        """Terms by kind. A term's space-free form is not counted as a second term."""
        return {k: sum(t.kind == k and not t.alias for t in self.terms.values()) for k in KINDS}


def is_guarded(wants_guard: bool, norm: str) -> bool:
    """A guard is only ever used on a single-token key."""
    return wants_guard and len(norm.split()) == 1


def parse_terms(path: Path, keys: Keys) -> ParsedTerms:
    """Reads kind|guard|term lines. Errors never quote the term."""
    parsed = ParsedTerms()
    if not path.exists():
        parsed.errors.append("terms file not found")
        return parsed
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|", 2)]
        if len(parts) != 3:
            parsed.errors.append(f"line {number}: expected kind|guard|term")
            continue
        kind, guard, term = parts
        if kind not in KINDS:
            parsed.errors.append(f"line {number}: unknown kind")
            continue
        if guard not in ("", "word"):
            parsed.errors.append(f"line {number}: guard must be empty or word")
            continue
        norm = keys.normalize(term)
        if not norm:
            parsed.errors.append(f"line {number}: term is empty after normalizing")
            continue
        if len(norm.split()) > MAX_TOKENS:
            parsed.errors.append(f"line {number}: term is longer than {MAX_TOKENS} tokens")
            continue
        guarded = is_guarded(guard == "word", norm)
        for index, form in enumerate(keys.forms(norm)):
            key = keys.hash(form)
            alias = index > 0
            existing = parsed.terms.get(key)
            if existing is None:
                parsed.terms[key] = ScreenTerm(kind, guarded, alias)
                continue
            if not alias and not existing.alias:
                parsed.merged += 1
            stronger = kind if KINDS.index(kind) < KINDS.index(existing.kind) else existing.kind
            parsed.terms[key] = ScreenTerm(stronger, guarded and existing.guarded, alias and existing.alias)
    return parsed


def screen_hits(
    text: str,
    terms: dict[str, ScreenTerm],
    keys: Keys,
    kinds: tuple[str, ...] = ("name", "deflect", "say"),
) -> set[str]:
    """Returns the kinds of term found in the text, never the terms."""
    return keys.scan(text, terms, kinds)
