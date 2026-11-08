"""Runs the pipeline through the real anthropic SDK against a local mock transport.

No request leaves the process. This checks what the fakes cannot: that the SDK
accepts these parameters, that the bytes on the wire are what the API expects,
and that the real stream objects are read correctly.
"""
import asyncio
import json

import anthropic
import httpx2
import pytest

from conftest import done, public_info, types, visible_text


def frame(event):
    return f"event: {event['type']}\ndata: {json.dumps(event)}\n\n".encode()


def stream_body(*events):
    return b"".join(frame(event) for event in events)


def start(model="claude-fable-5-1"):
    return {
        "type": "message_start",
        "message": {
            "id": "msg_1", "type": "message", "role": "assistant", "model": model, "content": [],
            "stop_reason": None, "stop_sequence": None,
            "usage": {"input_tokens": 500, "output_tokens": 1, "cache_read_input_tokens": 400, "cache_creation_input_tokens": 0},
        },
    }


def finish(stop_reason, output_tokens=60, iterations=None):
    delta_usage = {"output_tokens": output_tokens}
    if iterations:
        delta_usage["iterations"] = iterations
    return [
        {"type": "message_delta", "delta": {"stop_reason": stop_reason, "stop_sequence": None}, "usage": delta_usage},
        {"type": "message_stop"},
    ]


def block_start(index, block):
    return {"type": "content_block_start", "index": index, "content_block": block}


def block_delta(index, delta):
    return {"type": "content_block_delta", "index": index, "delta": delta}


def block_stop(index):
    return {"type": "content_block_stop", "index": index}


def thinking(index, signature):
    return [
        block_start(index, {"type": "thinking", "thinking": "", "signature": ""}),
        block_delta(index, {"type": "signature_delta", "signature": signature}),
        block_stop(index),
    ]


def text(index, value):
    return [
        block_start(index, {"type": "text", "text": "", "citations": None}),
        block_delta(index, {"type": "text_delta", "text": value}),
        block_stop(index),
    ]


def cited_text(index, value, source, position=0):
    return [
        block_start(index, {"type": "text", "text": "", "citations": None}),
        block_delta(index, {"type": "text_delta", "text": value}),
        block_delta(index, {"type": "citations_delta", "citation": {
            "type": "search_result_location", "cited_text": "He built it.", "source": source, "title": "T",
            "search_result_index": position, "start_block_index": 0, "end_block_index": 1,
        }}),
        block_stop(index),
    ]


def fallback(index):
    return [
        block_start(index, {
            "type": "fallback",
            "from": {"model": "claude-fable-5-1"},
            "to": {"model": "claude-opus-5"},
            "trigger": {"type": "refusal", "category": None},
        }),
        block_stop(index),
    ]


def extract_message(payload, stop_reason="end_turn"):
    return {
        "id": "msg_extract", "type": "message", "role": "assistant", "model": "claude-haiku-5-5",
        "content": [{"type": "text", "text": json.dumps(payload), "citations": None}],
        "stop_reason": stop_reason, "stop_sequence": None,
        "usage": {"input_tokens": 300, "output_tokens": 20},
    }


class Wire:
    def __init__(self, chat, monkeypatch, bodies):
        self.bodies = list(bodies)
        self.requests = []
        self.headers = []
        monkeypatch.setattr(chat, "new_client", self.client)

    def _handle(self, request):
        self.requests.append(json.loads(request.content))
        self.headers.append(request.headers)
        body = self.bodies.pop(0)
        if isinstance(body, dict):
            return httpx2.Response(200, json=body)
        return httpx2.Response(200, headers={"content-type": "text/event-stream"}, content=body)

    def client(self):
        return anthropic.AsyncAnthropic(
            api_key="not-a-real-key",
            max_retries=0,
            http_client=anthropic.DefaultAsyncHttpxClient(transport=httpx2.MockTransport(self._handle)),
        )


def test_real_client_builds_without_a_network_call(chat, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "not-a-real-key")
    client = chat.new_client()
    assert isinstance(client, anthropic.AsyncAnthropic)
    assert client.max_retries == 1
    asyncio.run(client.close())


def test_first_request_on_the_wire(deps, chat, monkeypatch):
    wire = Wire(chat, monkeypatch, [stream_body(start(), *cited_text(0, "He built a desktop automation engine.", "gui#overview"), *finish("end_turn"))])
    events = deps.run("What has he built?")
    body = wire.requests[0]
    assert body["model"] == "claude-fable-5-1"
    assert body["stream"] is True
    assert body["fallbacks"] == "default"
    assert "server-side-fallback-2026-07-01" in wire.headers[0]["anthropic-beta"]
    assert body["output_config"] == {"effort": "medium"}
    assert "thinking" not in body and "tool_choice" not in body and "temperature" not in body and "tools" not in body
    assert body["system"][-1]["cache_control"] == {"type": "ephemeral"}
    first_block = body["messages"][-1]["content"][0]
    assert first_block["type"] == "search_result" and first_block["citations"] == {"enabled": True}
    assert visible_text(events) == "He built a desktop automation engine."
    assert done(events)["cited"] == ["gui#overview"]


def test_multiple_text_blocks_join_without_added_breaks(deps, chat, monkeypatch):
    Wire(chat, monkeypatch, [stream_body(
        start(),
        *text(0, "He built "),
        *cited_text(1, "a desktop automation engine", "gui#overview"),
        *text(2, " for legacy systems."),
        *finish("end_turn"),
    )])
    assert visible_text(deps.run("What has he built?")) == "He built a desktop automation engine for legacy systems."


def test_usage_and_cost_from_the_real_stream(deps, chat, monkeypatch):
    Wire(chat, monkeypatch, [stream_body(start(), *text(0, "He built an engine for it."), *finish("end_turn", 60))])
    finished = done(deps.run("What has he built?"))
    assert finished["cost_usd"] == round((500 * 10 + 60 * 50 + 400 * 0.25) / 1_000_000, 2)
    row = deps.logged[0]
    assert row["cost_usd"] == pytest.approx((500 * 10 + 60 * 50 + 400 * 0.25) / 1_000_000, abs=1e-5)
    assert (row["input_tokens"], row["output_tokens"], row["cache_read_tokens"]) == (500, 60, 400)


def test_mid_output_fallback_on_the_real_stream(deps, chat, monkeypatch):
    iterations = [
        {"type": "message", "model": "claude-fable-5-1", "input_tokens": 500, "output_tokens": 30, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0},
        {"type": "fallback_message", "model": "claude-opus-5", "input_tokens": 400, "output_tokens": 40, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0},
    ]
    Wire(chat, monkeypatch, [stream_body(
        start(),
        *text(0, "These words came from the first model before it declined to go on, "),
        *fallback(1),
        *text(2, "and these words came from the second model."),
        *finish("end_turn", 40, iterations),
    )])
    events = deps.run("What has he built?")
    assert "retract" not in types(events)
    assert visible_text(events) == "These words came from the first model before it declined to go on, and these words came from the second model."
    finished = done(events)
    assert finished["model"] == "claude-opus-5"
    assert deps.logged[0]["cost_usd"] == pytest.approx((500 * 10 + 30 * 50 + 400 * 5 + 40 * 25) / 1_000_000, abs=1e-5)


def test_a_lookup_turn_on_the_wire(deps, chat, monkeypatch):
    deps.use_real_extract()
    deps.lookup_result = {"found": True, "summary": "Acme makes anvils.", "sources": [{"title": "Acme", "url": "https://acme.example"}]}
    wire = Wire(chat, monkeypatch, [
        extract_message({"kind": "company", "name": "Acme"}),
        stream_body(start(), *text(0, "He built an engine that relates."), *finish("end_turn")),
    ])
    events = deps.run("What relates to Acme?")
    assert deps.lookup_calls == [("company", "Acme")]
    assert visible_text(events) == "He built an engine that relates."
    assert done(events)["sources"]["web"] == [{"title": "Acme", "url": "https://acme.example"}]
    assert len(wire.requests) == 2

    extract, answer = wire.requests
    assert extract["model"] == "claude-haiku-5-5"
    assert extract["max_tokens"] == 100
    assert extract["thinking"] == {"type": "disabled"}
    assert extract["output_config"]["effort"] == "low"
    assert extract["output_config"]["format"]["type"] == "json_schema"
    assert extract["output_config"]["format"]["schema"]["properties"]["kind"]["enum"] == ["company", "technology", "industry", "empty"]
    assert extract["messages"] == [{"role": "user", "content": "What relates to Acme?"}]
    assert not {"tools", "tool_choice", "temperature", "stream"} & set(extract)
    assert "anthropic-beta" not in wire.headers[0]

    assert answer["stream"] is True
    assert not {"tools", "tool_choice"} & set(answer)
    assert public_info(answer) == {"found": True, "summary": "Acme makes anvils.", "extra_detail": "", "closest_work": []}
    assert [block["type"] for block in answer["messages"][-1]["content"]][-2:] == ["text", "text"]


def test_extraction_cost_on_the_wire(deps, chat, monkeypatch):
    deps.use_real_extract()
    Wire(chat, monkeypatch, [
        extract_message({"kind": "empty", "name": ""}),
        stream_body(start(), *text(0, "He built an engine for it."), *finish("end_turn", 60)),
    ])
    deps.run("What has he built?")
    expected = (500 * 10 + 60 * 50 + 400 * 0.25) / 1_000_000 + (300 * 0.10 + 20 * 0.50) / 1_000_000
    assert deps.logged[0]["cost_usd"] == pytest.approx(expected, abs=1e-5)
    assert deps.logged[0]["input_tokens"] == 500


def test_a_refused_extraction_on_the_wire_still_answers(deps, chat, monkeypatch):
    deps.use_real_extract()
    wire = Wire(chat, monkeypatch, [
        extract_message({"kind": "empty", "name": ""}, stop_reason="refusal"),
        stream_body(start(), *text(0, "He built an engine for it."), *finish("end_turn")),
    ])
    events = deps.run("What has he built?")
    assert visible_text(events) == "He built an engine for it."
    assert "lookup" not in types(events)
    assert "extract_failed" in deps.logged[0]["flags"]
    assert len(wire.requests) == 2


def test_web_lookup_on_the_wire(chat, monkeypatch):
    from conftest import ROOT, fake_screen, load_module

    module = load_module(ROOT / "frontend" / "api" / "chat.py", "site_chat_wire_copy")
    monkeypatch.setattr(module, "load_screen", lambda: fake_screen(module))
    monkeypatch.setattr(module, "web_cache_get", lambda key: None)
    monkeypatch.setattr(module, "web_cache_put", lambda *args: None)
    def message(content, stop):
        return {
            "id": "msg_2", "type": "message", "role": "assistant", "model": "claude-sonnet-5-5", "content": content,
            "stop_reason": stop, "stop_sequence": None,
            "usage": {"input_tokens": 1000, "output_tokens": 100, "server_tool_use": {"web_search_requests": 1, "web_fetch_requests": 0}},
        }

    search_blocks = [
        {"type": "server_tool_use", "id": "srvtoolu_1", "name": "web_search", "input": {"query": "acme"}},
        {"type": "web_search_tool_result", "tool_use_id": "srvtoolu_1", "content": [
            {"type": "web_search_result", "url": "https://acme.example", "title": "Acme", "encrypted_content": "ENC-CONTENT", "page_age": None},
        ]},
    ]
    wire = Wire(module, monkeypatch, [
        message(search_blocks, "pause_turn"),
        message([{"type": "text", "text": "Acme makes anvils.", "citations": [{
            "type": "web_search_result_location", "url": "https://acme.example", "title": "Acme",
            "cited_text": "anvils", "encrypted_index": "ENC-INDEX",
        }]}], "end_turn"),
    ])
    result = asyncio.run(module.web_lookup("company", "Acme"))
    assert result["found"] is True
    assert result["sources"] == [{"title": "Acme", "url": "https://acme.example"}]
    assert wire.requests[0]["tools"][0]["type"] == "web_search_20260209"
    assert wire.requests[0]["tools"][0]["max_uses"] == 1
    echoed = wire.requests[1]["messages"][1]
    assert echoed["role"] == "assistant"
    assert echoed["content"][1]["content"][0]["encrypted_content"] == "ENC-CONTENT"
