"""
bundle_extension.py

Builds the LeagueQL Chrome extension and bundles the production output into a
.zip file ready for upload to the Chrome Web Store Developer Dashboard.

The Chrome Web Store expects a zip of the *contents* of the extension's built
`dist/` directory (manifest.json at the top level), so that is what this script
produces.

Usage:
    # Activate the pipenv shell first (run once per session)
    pipenv shell

    # Build then zip (default output: <repo>/extension/<name>-<version>.zip)
    pipenv run python scripts/utility_scripts/bundle_extension.py

    # Skip `npm run build` and zip the existing dist/ as-is
    pipenv run python scripts/utility_scripts/bundle_extension.py --skip-build

    # Write the zip to a custom path
    pipenv run python scripts/utility_scripts/bundle_extension.py --output /tmp/extension.zip
"""

import argparse
import json
import logging
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

# scripts/utility_scripts/bundle_extension.py -> repo root is two levels up
REPO_ROOT = Path(__file__).resolve().parents[2]
EXTENSION_DIR = REPO_ROOT / "extension"
DIST_DIR = EXTENSION_DIR / "dist"


def read_extension_version() -> str:
    """Read the extension version from extension/package.json."""
    package_json = EXTENSION_DIR / "package.json"
    try:
        data = json.loads(package_json.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Could not read %s: %s", package_json, exc)
        sys.exit(1)
    return data.get("version", "0.0.0")


def run_build() -> None:
    """Run `npm run build` inside the extension directory."""
    npm = shutil.which("npm")
    if npm is None:
        logger.error(
            "`npm` was not found on PATH. Install Node.js or use --skip-build."
        )
        sys.exit(1)

    logger.info("Building extension (npm run build)…")
    try:
        subprocess.run([npm, "run", "build"], cwd=EXTENSION_DIR, check=True)
    except subprocess.CalledProcessError as exc:
        logger.error("Build failed with exit code %d.", exc.returncode)
        sys.exit(exc.returncode)


def zip_dist(output_path: Path) -> int:
    """
    Zip the contents of dist/ (not the dist/ folder itself) into output_path.
    Returns the number of files written.
    """
    if not DIST_DIR.is_dir():
        logger.error(
            "dist/ not found at %s. Run a build first (omit --skip-build).", DIST_DIR
        )
        sys.exit(1)

    files = sorted(p for p in DIST_DIR.rglob("*") if p.is_file())
    if not files:
        logger.error("dist/ is empty — nothing to bundle.")
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in files:
            arcname = file.relative_to(DIST_DIR)
            zf.write(file, arcname)
            logger.debug("Added %s", arcname)

    return len(files)


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Build and bundle the LeagueQL Chrome extension into a .zip."
    )
    p.add_argument(
        "--skip-build",
        action="store_true",
        default=False,
        help="Skip `npm run build` and zip the existing dist/ as-is.",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output zip path (default: extension/leagueql-espn-extension-<version>.zip).",
    )
    p.add_argument("--debug", action="store_true", help="Enable DEBUG logging.")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    version = read_extension_version()
    output_path = args.output or (
        EXTENSION_DIR / f"leagueql-espn-extension-{version}.zip"
    )

    if args.skip_build:
        logger.info("Skipping build — bundling existing dist/.")
    else:
        run_build()

    count = zip_dist(output_path)
    size_kb = output_path.stat().st_size / 1024
    logger.info(
        "Done. Bundled %d file(s) into %s (%.1f KB).", count, output_path, size_kb
    )


if __name__ == "__main__":
    main()
