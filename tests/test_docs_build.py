import json
import pathlib
import sys

import pytest

pytest.importorskip("fastapi", reason="REST interface deps not installed")

# Resolved from this file, not the working directory, so the suite runs from anywhere.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import build_docs


def test_build_writes_a_page_and_a_schema(tmp_path):
    out = build_docs.build(tmp_path / "site")

    assert (out / "index.html").exists()
    assert (out / "openapi.json").exists()
    # Without .nojekyll, Pages runs the output through Jekyll and can drop files.
    assert (out / ".nojekyll").exists()


def test_the_schema_points_try_it_out_at_the_live_service(tmp_path):
    build_docs.build(tmp_path / "site")
    schema = json.loads((tmp_path / "site" / "openapi.json").read_text())

    # Without an explicit server, Swagger UI resolves calls relative to github.io,
    # where no API exists, and every Try-it-out 404s.
    assert schema["servers"], "openapi.json must declare a server"
    assert schema["servers"][0]["url"].startswith("https://")


def test_the_schema_carries_every_endpoint_and_the_auth_scheme(tmp_path):
    build_docs.build(tmp_path / "site")
    schema = json.loads((tmp_path / "site" / "openapi.json").read_text())

    for path in ("/health", "/orders", "/positions", "/orders/history"):
        assert path in schema["paths"]
    assert "APIKeyHeader" in schema["components"]["securitySchemes"]


def test_the_page_warns_about_the_cold_start_and_the_key(tmp_path):
    # A visitor who does not know the instance sleeps reads a 45 second wait as a
    # broken link, and one who does not know about the key reads 401 as a bug.
    html = (build_docs.build(tmp_path / "site") / "index.html").read_text()

    assert "X-API-Key" in html
    assert "45 seconds" in html
    assert build_docs.API_URL in html
