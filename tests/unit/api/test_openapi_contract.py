"""Contract test: FastAPI's generated schema must match docs/api/openapi_spec.yaml.

The checked-in spec is hand-maintained, so it can silently drift from the routes.
This compares the parts FastAPI can reliably describe: the set of paths, the HTTP
methods per path, declared path/query parameters, and the success status code.

Error responses (4xx/5xx) are intentionally *not* compared: handlers raise
``HTTPException`` rather than declaring ``responses=``, so FastAPI only emits a
generic ``422``. The hand-written spec is the source of truth for those.
"""

from pathlib import Path

import pytest
import yaml

SPEC_PATH = Path(__file__).resolve().parents[3] / "docs" / "api" / "openapi_spec.yaml"
HTTP_METHODS = ("get", "put", "post", "delete", "patch")

# Operations whose real success status can't be expressed through FastAPI's schema.
# The Yahoo OAuth callback returns a RedirectResponse (302) from a handler FastAPI
# documents as a plain 200. Keyed by (path, method) -> status the spec must declare.
SUCCESS_STATUS_OVERRIDES = {
    ("/leagues/yahoo/oauth/callback", "get"): "302",
}


@pytest.fixture(scope="module")
def generated():
    import main

    return main.app.openapi()["paths"]


@pytest.fixture(scope="module")
def documented():
    with SPEC_PATH.open() as f:
        return yaml.safe_load(f)["paths"]


def _operations(paths):
    return {
        (path, method): op
        for path, item in paths.items()
        for method, op in item.items()
        if method in HTTP_METHODS
    }


def _params(op, location):
    return {p["name"] for p in op.get("parameters", []) if p.get("in") == location}


def _success_statuses(op):
    return {s for s in op.get("responses", {}) if s[0] in "23"}


def test_spec_file_exists_and_has_paths(documented):
    assert documented, "docs/api/openapi_spec.yaml declares no paths"


def test_every_route_is_documented(generated, documented):
    missing = sorted(set(_operations(generated)) - set(_operations(documented)))
    assert not missing, f"Routes missing from docs/api/openapi_spec.yaml: {missing}"


def test_every_documented_operation_exists(generated, documented):
    stale = sorted(set(_operations(documented)) - set(_operations(generated)))
    assert not stale, f"Operations in the spec with no matching route: {stale}"


def test_path_and_query_parameters_match(generated, documented):
    gen, doc = _operations(generated), _operations(documented)
    drift = []
    for key in sorted(set(gen) & set(doc)):
        for location in ("path", "query"):
            g, d = _params(gen[key], location), _params(doc[key], location)
            if g != d:
                drift.append(f"{key} {location}: code={sorted(g)} spec={sorted(d)}")
    assert not drift, "Parameter drift:\n" + "\n".join(drift)


def test_success_status_codes_match(generated, documented):
    gen, doc = _operations(generated), _operations(documented)
    drift = []
    for key in sorted(set(gen) & set(doc)):
        expected = SUCCESS_STATUS_OVERRIDES.get(key)
        g = {expected} if expected else _success_statuses(gen[key])
        d = _success_statuses(doc[key])
        if g != d:
            drift.append(f"{key}: code={sorted(g)} spec={sorted(d)}")
    assert not drift, "Success status drift:\n" + "\n".join(drift)
