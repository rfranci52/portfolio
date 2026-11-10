"""Checks on the deployed page: its response headers, pinned dependencies and a few page rules."""
import ast
import json
import os
import re
import shutil
import struct
import subprocess

import pytest

from conftest import ROOT

FRONTEND = ROOT / "frontend"
SRC = FRONTEND / "src"
NODE = shutil.which("node", path=os.pathsep.join([os.environ.get("PATH", ""), "/opt/homebrew/bin", "/usr/local/bin"]))


def vercel_headers():
    config = json.loads((FRONTEND / "vercel.json").read_text(encoding="utf-8"))
    rule = next(item for item in config["headers"] if item["source"] == "/(.*)")
    return {item["key"]: item["value"] for item in rule["headers"]}


def csp_directives():
    policy = vercel_headers()["Content-Security-Policy-Report-Only"]
    return {part.split()[0]: part.split()[1:] for part in policy.split(";")}


def test_the_basic_security_headers_are_sent():
    headers = vercel_headers()
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in headers["Permissions-Policy"] and "geolocation=()" in headers["Permissions-Policy"]


def test_the_content_policy_only_reports_for_now():
    assert "Content-Security-Policy" not in vercel_headers()


def test_the_rest_of_the_deployment_settings_are_kept():
    config = json.loads((FRONTEND / "vercel.json").read_text(encoding="utf-8"))
    assert config["functions"]["api/chat.py"]["maxDuration"] == 60
    assert config["rewrites"] == [{"source": "/((?!api/).*)", "destination": "/index.html"}]


@pytest.mark.parametrize("directive,expected", [
    ("default-src", ["'none'"]),
    ("script-src", ["'self'"]),
    ("style-src", ["'self'"]),
    ("img-src", ["'self'", "data:"]),
    ("media-src", ["'self'"]),
    ("font-src", ["'self'"]),
    ("connect-src", ["'self'"]),
    ("base-uri", ["'none'"]),
    ("form-action", ["'self'"]),
    ("frame-ancestors", ["'none'"]),
])
def test_the_content_policy_is_the_agreed_one(directive, expected):
    assert csp_directives()[directive] == expected


def source_files():
    return [path for path in SRC.rglob("*") if path.suffix in (".ts", ".tsx")]


def test_the_page_has_nothing_the_content_policy_would_block():
    for path in source_files():
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"\bstyle=\{", text), path.name
        assert "dangerouslySetInnerHTML" not in text, path.name
    index = (FRONTEND / "index.html").read_text(encoding="utf-8")
    assert "<style" not in index and not re.search(r"<script(?![^>]*\bsrc=)", index)


def test_every_request_the_page_makes_stays_on_the_site():
    for path in source_files():
        text = path.read_text(encoding="utf-8")
        for call in re.findall(r"(?:fetch|sendBeacon\??\.?)\(\s*['\"`]([^'\"`]+)", text):
            assert call.startswith("/api/"), (path.name, call)


def test_the_video_is_served_from_the_site():
    projects = json.loads((SRC / "projects.json").read_text(encoding="utf-8"))
    videos = [project["video_url"] for project in projects if project.get("video_url")]
    assert videos and all(video.startswith("/") and not video.startswith("//") for video in videos)


def test_python_dependencies_are_exact_versions():
    lines = [line.strip() for line in (FRONTEND / "requirements.txt").read_text(encoding="utf-8").splitlines()]
    pins = [line for line in lines if line and not line.startswith("#")]
    assert pins and all(re.fullmatch(r"[a-z0-9._-]+==[0-9][\w.]*", line) for line in pins), pins
    names = {line.split("==")[0] for line in pins}
    assert {"anthropic", "psycopg", "psycopg-binary", "httpx2", "pydantic"} <= names


def test_the_router_is_on_a_fixed_version():
    package = json.loads((FRONTEND / "package.json").read_text(encoding="utf-8"))
    version = package["dependencies"]["react-router-dom"]
    assert re.fullmatch(r"\d+\.\d+\.\d+", version)
    major, minor, patch = (int(part) for part in version.split("."))
    assert (major, minor, patch) >= (7, 18, 2)


def page(name):
    return (SRC / name).read_text(encoding="utf-8")


def test_the_contact_form_has_a_hidden_field_people_cannot_reach():
    text = page("pages/Contact.tsx")
    assert 'name="extra"' in text and "tabIndex={-1}" in text and 'autoComplete="off"' in text
    assert 'aria-hidden="true"' in text and "-left-[9999px]" in text
    assert "extra: ''" in text


def test_the_contact_form_shows_what_the_server_said_when_it_refuses():
    assert "error.message" in page("pages/Contact.tsx") and "instanceof ContactError" in page("pages/Contact.tsx")
    assert "if (!res.ok || !body?.ok) throw new ContactError" in page("api.ts")


def test_the_contact_form_limits_match_what_the_server_keeps():
    text = page("pages/Contact.tsx")
    assert "maxLength={200}" in text and "maxLength={320}" in text and "maxLength={5000}" in text


def test_a_web_source_shows_its_hostname():
    text = page("components/ChatTurn.tsx")
    assert "{source.host}" in text and "new URL(href).hostname" in text


def test_the_note_on_what_is_saved_is_linked_from_every_page():
    app = page("App.tsx")
    footer = app[app.index("function Footer"):app.index("export default function App")]
    assert 'to="/what-is-saved"' in footer
    assert 'path="/what-is-saved"' in app


@pytest.mark.parametrize("words", [
    "scrolled", "clicked", "visitor ID", "session ID", "IP", "approximate location", "browser details",
    "questions and the answers", "name, email address and message", "web analytics",
])
def test_the_note_names_what_is_recorded(words):
    assert words in page("pages/WhatIsSaved.tsx")


def test_the_note_does_not_mention_a_network_lookup_that_is_not_running():
    text = page("pages/WhatIsSaved.tsx").lower()
    assert "network" not in text and "\u2014" not in text


@pytest.mark.skipif(NODE is None, reason="node is not installed")
@pytest.mark.parametrize("url,expected", [
    ("https://example.test/page", "https://example.test/page"),
    ("  https://example.test/ ", "https://example.test/"),
    ("HTTPS://EXAMPLE.TEST/", "https://example.test/"),
    ("http://example.test/page", None),
    ("https://user@example.test/", None),
    ("https://user:secret@example.test/", None),
    ("https://rakimfrancis.com@example.test/", None),
    ("javascript:alert(1)", None),
    ("data:text/html,x", None),
    ("//example.test/", None),
    ("not a url", None),
])
def test_web_source_links_must_be_plain_https(url, expected):
    links = (SRC / "chat" / "links.ts").as_uri()
    code = f"import {{ webHref }} from {json.dumps(links)}; console.log(JSON.stringify(webHref({json.dumps(url)})))"
    result = subprocess.run([NODE, "--no-warnings", "--input-type=module", "-e", code], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == expected


def test_the_sitemap_lists_every_page_and_project():
    sitemap = (FRONTEND / "public" / "sitemap.xml").read_text(encoding="utf-8")
    listed = re.findall(r"<loc>https://www\.rakimfrancis\.com(/[^<]*)</loc>", sitemap)
    routes = set(re.findall(r'<Route path="(/[^"]*)"', page("App.tsx")))
    pages = {route for route in routes if ":" not in route and route != "/about"}  # /about only redirects home
    projects = json.loads((SRC / "projects.json").read_text(encoding="utf-8"))
    assert len(listed) == len(set(listed))
    assert set(listed) == pages | {f"/projects/{project['slug']}" for project in projects}
    assert "Sitemap: https://www.rakimfrancis.com/sitemap.xml" in (FRONTEND / "public" / "robots.txt").read_text(encoding="utf-8")


def test_an_unknown_address_gets_the_not_found_page():
    assert '<Route path="*" element={<NotFound />} />' in page("App.tsx")
    assert "if (error) return <NotFound />" in page("pages/ProjectDetail.tsx")
    text = page("pages/NotFound.tsx")
    assert "Page not found" in text and "That address isn't on this site." in text
    assert 'to="/"' in text and 'to="/projects"' in text


def test_link_previews_have_an_image_and_the_canonical_address():
    index = (FRONTEND / "index.html").read_text(encoding="utf-8")
    for tag in (
        '<link rel="canonical" href="https://www.rakimfrancis.com/" />',
        '<meta property="og:url" content="https://www.rakimfrancis.com/" />',
        '<meta property="og:image" content="https://www.rakimfrancis.com/og-image.png" />',
        '<meta name="twitter:card" content="summary_large_image" />',
    ):
        assert tag in index
    png = (FRONTEND / "public" / "og-image.png").read_bytes()
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", png[16:24]) == (1200, 627)


def seed_projects():
    """The Project(...) rows in backend/app/seed.py, read without importing it."""
    tree = ast.parse((ROOT / "backend" / "app" / "seed.py").read_text(encoding="utf-8"))
    rows = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "Project":
            row = {keyword.arg: ast.literal_eval(keyword.value) for keyword in node.keywords}
            rows[row["slug"]] = row
    return rows


def test_the_baked_projects_match_the_seed():
    # dump_projects.py rebuilds projects.json from seed.py, so the two must not drift apart.
    seed = seed_projects()
    baked = {project["slug"]: project for project in json.loads((SRC / "projects.json").read_text(encoding="utf-8"))}
    assert set(seed) == set(baked)
    defaults = {"repo_url": None, "demo_url": None, "video_url": None, "featured": False, "sort_order": 0}
    for slug, row in seed.items():
        for field in ("title", "tagline", "summary", "tech", "highlights", "sections", *defaults):
            assert row.get(field, defaults.get(field)) == baked[slug][field], (slug, field)
