"""Guard: the Lambda packaging script must ship local subpackages (api/routes/).

The script copies top-level ``*.py`` files and ``common/``; a subpackage is only
included by its dedicated copy step. If that step regresses, the API Lambda would
cold-start with ``ModuleNotFoundError: routes``, which no other test would catch.
This runs the script's real subpackage-copy snippet against a temp build dir.
"""

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "deployment_scripts" / "build_lambda_zip.sh"
START = "# Copy any local subpackages"
END = "# Copy the shared common package"


def _subpackage_snippet() -> str:
    text = SCRIPT.read_text()
    assert START in text and END in text, "subpackage copy step missing from script"
    return text[text.index(START) : text.index(END)]


def test_api_routes_package_is_copied_into_build_dir(tmp_path):
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    source_dir = REPO / "src" / "api"

    # Seed a __pycache__ in the *source* package to prove it isn't shipped.
    pycache = source_dir / "routes" / "__pycache__"
    pycache.mkdir(exist_ok=True)

    subprocess.run(  # noqa: S603
        ["bash", "-c", f"set -euo pipefail\n{_subpackage_snippet()}"],  # noqa: S607
        env={
            "SOURCE_DIR": str(source_dir),
            "BUILD_DIR": str(build_dir),
            "PATH": "/usr/bin:/bin",
        },
        check=True,
    )

    shipped = {p.name for p in (build_dir / "routes").glob("*.py")}
    expected = {p.name for p in (source_dir / "routes").glob("*.py")}
    assert "__init__.py" in shipped
    assert shipped == expected
    assert not list((build_dir / "routes").rglob("__pycache__"))
