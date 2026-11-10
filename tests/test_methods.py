"""Wrong request methods get a short JSON 405, not the standard library's HTML error page.

These run the real request parsing on a local port, because that is where the default page
comes from; run_handler in scripts/dev_api.py calls do_POST directly and never reaches it.
"""
import http.client
import json
import socket
import threading
from http.server import ThreadingHTTPServer

import pytest

from conftest import ROOT, load_module


@pytest.fixture(params=["contact", "track"])
def port(request):
    module = load_module(ROOT / "frontend" / "api" / f"{request.param}.py", f"site_{request.param}_for_method_tests")

    class Quiet(module.handler):
        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Quiet)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server.server_address[1]
    server.shutdown()
    server.server_close()


def send(port, method):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        conn.request(method, "/")
        resp = conn.getresponse()
        return resp.status, dict(resp.getheaders()), resp.read()
    finally:
        conn.close()


@pytest.mark.parametrize("method", ["GET", "PUT", "PATCH", "OPTIONS", "DELETE"])
def test_other_methods_get_a_json_405(port, method):
    status, headers, body = send(port, method)
    assert status == 405
    assert headers["Allow"] == "POST"
    assert headers["Content-Type"] == "application/json"
    assert json.loads(body) == {"error": "method not allowed"}


def test_head_gets_a_405_with_no_body(port):
    status, headers, body = send(port, "HEAD")
    assert status == 405
    assert body == b""


def test_a_malformed_request_gets_json_not_html(port):
    with socket.create_connection(("127.0.0.1", port), timeout=5) as sock:
        sock.sendall(b"GET / NOT-A-VERSION\r\n\r\n")
        data = b""
        while chunk := sock.recv(4096):
            data += chunk
    assert b"<html" not in data.lower()
    assert b'"request refused"' in data


def test_post_still_reaches_the_handler(port):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        conn.request("POST", "/", body=b"{}", headers={"Content-Type": "application/json", "Origin": "https://evil.example"})
        assert conn.getresponse().status == 403
    finally:
        conn.close()
