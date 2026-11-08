"""Shared fakes. Nothing in the test suite touches a network or a database."""
import asyncio
import copy
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

ROOT = Path(__file__).resolve().parents[1]
PEPPER = "test-pepper"

# Invented terms, one of each behavior the screen has to tell apart.
TERMS = [
    ("name", False, "zephyrion dynamics"),
    ("name", True, "quillon"),
    ("name", False, "alpha beta gamma delta epsilon"),
    ("deflect", False, "moonbase blueprints"),
    ("self", False, "rakim francis"),
    ("say", False, "vermilion protocol"),
]

PASSAGES = [
    {
        "id": "gui#overview", "doc": "gui-automation", "title": "GUI Automation", "section": "Overview",
        "url": "/projects/gui-automation", "content": "He built a desktop automation engine.",
        "snippet": "He built a desktop automation engine.", "score": 0.032,
    },
    {
        "id": "trading#lessons", "doc": "algorithmic-trading", "title": "Algorithmic Trading", "section": "Lessons",
        "url": "/projects/algorithmic-trading", "content": "He rebuilt a trading system around one hard lesson.",
        "snippet": "He rebuilt a trading system around one hard lesson.", "score": 0.016,
    },
]


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def fake_screen(chat_module):
    terms = {
        chat_module.hash_key(form, PEPPER): {"kind": kind, "guarded": guarded}
        for kind, guarded, term in TERMS
        for form in chat_module.key_forms(term)
    }
    return {"terms": terms, "policy_addendum": "addendum for tests", "decoys": ["Harborline Freight Group", "Cedar Point Labs"]}


@pytest.fixture(scope="session")
def chat_module():
    return load_module(ROOT / "frontend" / "api" / "chat.py", "site_chat_for_tests")


@pytest.fixture
def chat(chat_module, monkeypatch):
    for name in (
        "SITE_MODEL", "SITE_EFFORT", "SITE_EXTRACT_MODEL", "SITE_ALLOWED_ORIGINS", "IPINFO_TOKEN", "ORG_CONTEXT_ENABLED",
        "WEB_LOOKUP_ENABLED", "SITE_DAILY_SPEND_USD", "SITE_MONTHLY_SPEND_USD", "SITE_STOP_ON_DISCONNECT",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SITE_HASH_PEPPER", PEPPER)
    monkeypatch.setattr(chat_module, "load_screen", lambda: fake_screen(chat_module))
    chat_module.reset_state()
    yield chat_module
    chat_module.reset_state()


def usage(input_tokens=100, output_tokens=50, cache_read=0, cache_write=0, iterations=None, searches=0):
    server = NS(web_search_requests=searches) if searches else None
    return NS(
        input_tokens=input_tokens, output_tokens=output_tokens, cache_read_input_tokens=cache_read,
        cache_creation_input_tokens=cache_write, iterations=iterations, server_tool_use=server,
    )


def text_event(text):
    return NS(type="content_block_delta", delta=NS(type="text_delta", text=text))


def fallback_block(to_model="claude-opus-5", from_model="claude-fable-5-1"):
    return NS(type="fallback", to=NS(model=to_model), from_=NS(model=from_model))


def fallback_event(to_model="claude-opus-5"):
    return NS(type="content_block_start", content_block=fallback_block(to_model))


def text_block(text, citations=None):
    return NS(type="text", text=text, citations=citations)


def citation(source):
    return NS(type="search_result_location", source=source)


def thinking_block(signature="sig-1"):
    return NS(type="thinking", thinking="", signature=signature)


def model_turn(chunks=(), content=None, stop_reason="end_turn", extra_events=(), raises=None, model="claude-fable-5-1", use=None):
    """One scripted model response: streamed text plus the final message it ends with."""
    events = [NS(type="message_start", message=NS(model=model, usage=usage(output_tokens=1)))]
    events.extend(extra_events)
    events.extend(text_event(chunk) for chunk in chunks)
    if content is None:
        content = [text_block("".join(chunks))] if chunks else []
    final = NS(model=model, content=content, stop_reason=stop_reason, usage=use or usage())
    return NS(events=events, final=final, raises=raises)


class FakeStream:
    def __init__(self, scripted):
        self.scripted = scripted
        self.closed = False
        self.consumed = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        self.closed = True

    def __aiter__(self):
        return self._events()

    async def _events(self):
        for event in self.scripted.events:
            self.consumed += 1
            yield event
        if self.scripted.raises:
            raise self.scripted.raises

    async def get_final_message(self):
        return self.scripted.final


class FakeClient:
    """Stands in for AsyncAnthropic and records every request it is given."""

    def __init__(self, turns=()):
        self.turns = list(turns)
        self.requests = []
        self.streams = []
        self.created = []
        self.responses = []
        self.beta = NS(messages=NS(stream=self._stream))
        self.messages = NS(create=self._create)

    def _stream(self, **kwargs):
        self.requests.append(copy.deepcopy(kwargs))
        stream = FakeStream(self.turns.pop(0))
        self.streams.append(stream)
        return stream

    async def _create(self, **kwargs):
        self.created.append(copy.deepcopy(kwargs))
        return self.responses.pop(0)

    async def close(self):
        pass


class Deps:
    """Every network dependency of the pipeline, replaced and recorded."""

    def __init__(self, chat, monkeypatch):
        self.chat = chat
        self.client = FakeClient()
        self.monkeypatch = monkeypatch
        self.real_extract = chat.extract_subject
        self.extract_calls = []
        self.subject = None  # what the extraction step reports, or an Exception it raises
        self.embed_calls = []
        self.search_calls = []
        self.org_calls = []
        self.lookup_calls = []
        self.quota_calls = []
        self.log_slot_calls = []
        self.spend_recorded = []
        self.spend_checks = 0
        self.logged = []
        self.passages = list(PASSAGES)
        self.org_rows = []
        self.lookup_result = {"found": False}
        self.quota_allowed = True
        self.spend_allowed = True
        self.log_slot_allowed = True
        for name, replacement in {
            "new_client": lambda: self.client,
            "extract_subject": self._extract,
            "embed_query": self._embed,
            "search_chunks": self._search,
            "lookup_org_db": self._org,
            "web_lookup": self._lookup,
            "take_quota_db": self._quota,
            "take_log_slot_db": self._log_slot,
            "spend_open_db": self._spend_open,
            "record_spend_db": self.spend_recorded.append,
            "write_log": self.logged.append,
        }.items():
            monkeypatch.setattr(chat, name, replacement)

    def use_real_extract(self):
        """Put the real extraction step back, so its request goes through the fake client."""
        self.monkeypatch.setattr(self.chat, "extract_subject", self.real_extract)

    def _extract(self, text):
        self.extract_calls.append(text)
        if isinstance(self.subject, Exception):
            raise self.subject
        return {"kind": "empty", "name": "", "cost_usd": 0.0, "ok": True, **(self.subject or {})}

    def _embed(self, text):
        self.embed_calls.append(text)
        return [0.1, 0.2]

    def _search(self, embedding, query_text):
        self.search_calls.append((embedding, query_text))
        return list(self.passages)

    def _org(self, hashes):
        self.org_calls.append(list(hashes))
        return list(self.org_rows)

    def _lookup(self, kind, name):
        self.lookup_calls.append((kind, name))
        if isinstance(self.lookup_result, Exception):
            raise self.lookup_result
        return self.lookup_result

    def _quota(self, ip):
        self.quota_calls.append(ip)
        if isinstance(self.quota_allowed, Exception):
            raise self.quota_allowed
        return self.quota_allowed

    def _log_slot(self, ip):
        self.log_slot_calls.append(ip)
        if isinstance(self.log_slot_allowed, Exception):
            raise self.log_slot_allowed
        return self.log_slot_allowed

    def _spend_open(self):
        self.spend_checks += 1
        if isinstance(self.spend_allowed, Exception):
            raise self.spend_allowed
        return self.spend_allowed

    def script(self, *turns):
        self.client.turns = list(turns)

    def signed(self, message):
        """An earlier assistant turn as the page would send it back."""
        if message["role"] != "assistant":
            return message
        return {**message, "signature": self.chat.sign_turn(message["content"].strip())}

    def run(self, text=None, messages=None):
        turns = [self.signed(m) for m in messages] if messages else [{"role": "user", "content": text}]
        return run_chat(self.chat, turns)


def make_request(messages):
    return {
        "messages": messages, "session_id": "s1", "visitor_id": "v1", "page": "/", "referrer": "",
        "ip": "203.0.113.9", "city": "Testville", "region": "NY", "country": "US", "user_agent": "pytest",
    }


def run_chat(chat, messages):
    async def collect():
        return [event async for event in chat.chat_events(make_request(messages))]

    return asyncio.run(collect())


def types(events):
    return [event["type"] for event in events]


def visible_text(events):
    """What a visitor ends up looking at."""
    text = ""
    for event in events:
        if event["type"] == "delta":
            text += event["text"]
        elif event["type"] == "retract":
            text = event["text"]
    return text


def done(events):
    return next(event for event in events if event["type"] == "done")


def public_info_blocks(request):
    """The text of each block of public information in the question of one model request."""
    return [
        block["text"] for block in request["messages"][-1]["content"]
        if block["type"] == "text" and block["text"].startswith("<public_information>")
    ]


def public_info(request):
    """The one lookup payload a model request carries, parsed."""
    blocks = public_info_blocks(request)
    assert len(blocks) == 1
    return json.loads(blocks[0].split("\n")[2])


def dump(value):
    return json.dumps(value, default=lambda item: vars(item)).lower()


@pytest.fixture
def deps(chat, monkeypatch):
    return Deps(chat, monkeypatch)
