#!/usr/bin/env python
"""Local API server for development, matching the deployed routes on port 8787.

    python scripts/dev_api.py --env-file PATH [--env-file PATH ...] [--port 8787]

Serves /api/chat from its ASGI app and wraps the /api/track and /api/contact
handlers. Settings come from the process environment first, then from each
--env-file in order. Values are parsed here, never handed to a shell or printed.
"""
import argparse
import asyncio
import email.message
import importlib.util
import io
import os
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parent.parent / "frontend" / "api"
DEV_ORIGINS = "localhost,127.0.0.1"  # the deployed functions only serve the real site


def parse_env_file(path):
    """KEY=VALUE lines as a dict. Quotes around a value are removed."""
    values = {}
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
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


def load_env(paths):
    for path in paths:
        for key, value in parse_env_file(path).items():
            os.environ.setdefault(key, value)
    os.environ.setdefault("SITE_ALLOWED_ORIGINS", DEV_ORIGINS)


def load_api_module(name):
    spec = importlib.util.spec_from_file_location(f"site_api_{name}", API_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run_handler(handler_class, method, path, headers, body):
    """Run a BaseHTTPRequestHandler in memory. Returns (status, header list, body)."""

    class Bridge(handler_class):
        def __init__(self):
            self.rfile = io.BytesIO(body)
            self.wfile = io.BytesIO()
            self.headers = email.message.Message()
            for key, value in headers:
                self.headers[key] = value
            self.command = method
            self.path = path
            self.request_version = "HTTP/1.1"
            self.requestline = f"{method} {path} HTTP/1.1"
            self.client_address = ("127.0.0.1", 0)

        def log_message(self, *args):
            pass

    bridge = Bridge()
    getattr(bridge, f"do_{method}")()
    head, _, payload = bridge.wfile.getvalue().partition(b"\r\n\r\n")
    lines = head.decode("latin-1").split("\r\n")
    status = int(lines[0].split()[1])
    response_headers = [
        (name.strip().lower().encode("latin-1"), value.strip().encode("latin-1"))
        for name, value in (line.split(":", 1) for line in lines[1:] if ":" in line)
    ]
    return status, response_headers, payload


async def _read_all(receive):
    chunks = []
    while True:
        message = await receive()
        if message["type"] != "http.request":
            return b"".join(chunks)
        chunks.append(message.get("body", b""))
        if not message.get("more_body"):
            return b"".join(chunks)


def make_router(chat_app, handlers):
    """An ASGI router: chat_app at /api/chat, and {path: handler class} for the rest."""

    async def router(scope, receive, send):
        if scope["type"] == "lifespan":
            await chat_app(scope, receive, send)
            return
        if scope["type"] != "http":
            return
        if scope["path"].rstrip("/") == "/api/chat":
            await chat_app(scope, receive, send)
            return
        handler_class = handlers.get(scope["path"].rstrip("/"))
        if handler_class is None or scope["method"] != "POST":
            await send({"type": "http.response.start", "status": 404, "headers": []})
            await send({"type": "http.response.body", "body": b"not found"})
            return
        body = await _read_all(receive)
        headers = [(key.decode("latin-1"), value.decode("latin-1")) for key, value in scope["headers"]]
        status, response_headers, payload = await asyncio.to_thread(
            run_handler, handler_class, scope["method"], scope["path"], headers, body,
        )
        await send({"type": "http.response.start", "status": status, "headers": response_headers})
        await send({"type": "http.response.body", "body": payload})

    return router


def main():
    parser = argparse.ArgumentParser(description="Local API server for development")
    parser.add_argument("--env-file", action="append", default=[], help="KEY=VALUE file, may be repeated")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    load_env(args.env_file)

    import uvicorn

    chat = load_api_module("chat")
    handlers = {
        "/api/track": load_api_module("track").handler,
        "/api/contact": load_api_module("contact").handler,
    }
    uvicorn.run(make_router(chat.app, handlers), host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
