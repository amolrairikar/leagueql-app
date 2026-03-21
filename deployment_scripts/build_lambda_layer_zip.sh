#!/bin/bash
# =============================================================================
# create_lambda_layer.sh
# Creates an AWS Lambda layer zip for a given Python package.
#
# Usage:
#   ./create_lambda_layer.sh <package_name> [python_version]
#
# Examples:
#   ./create_lambda_layer.sh pandas
#   ./create_lambda_layer.sh pandas 3.11
#   ./create_lambda_layer.sh "scikit-learn" 3.12
# =============================================================================
 
set -euo pipefail
 
# ── Args ─────────────────────────────────────────────────────────────────────
PACKAGE_NAME="${1:-}"
PYTHON_VERSION="${2:-3.13}"
 
if [[ -z "$PACKAGE_NAME" ]]; then
  echo "❌  Usage: $0 <package_name> [python_version]"
  echo "   Example: $0 pandas 3.12"
  exit 1
fi
 
# Derive a filesystem-safe name (e.g. "scikit-learn" → "scikit_learn")
SAFE_NAME="${PACKAGE_NAME//-/_}"
PYTHON_MINOR="python${PYTHON_VERSION}"          # e.g. python3.12
LAYER_DIR="lambda_layer_${SAFE_NAME}"
SITE_PACKAGES_PATH="${LAYER_DIR}/python/lib/${PYTHON_MINOR}/site-packages"
OUTPUT_ZIP="${SAFE_NAME}_lambda_layer.zip"
 
# ── Checks ────────────────────────────────────────────────────────────────────
if ! command -v pip3 &>/dev/null && ! command -v pip &>/dev/null; then
  echo "❌  pip is not installed or not on PATH."
  exit 1
fi
 
if ! command -v zip &>/dev/null; then
  echo "❌  zip is not installed. Install it and re-run."
  exit 1
fi
 
PIP_CMD="$(command -v pip3 || command -v pip)"
 
# ── Build ─────────────────────────────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📦  Package       : ${PACKAGE_NAME}"
echo "  🐍  Python version: ${PYTHON_VERSION}"
echo "  📂  Layer dir     : ${LAYER_DIR}/"
echo "  🗜   Output zip    : ${OUTPUT_ZIP}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
 
# Clean any previous build artifacts
rm -rf "${LAYER_DIR}" "${OUTPUT_ZIP}"
 
# Lambda requires packages at:  python/lib/pythonX.Y/site-packages/
# This makes `import <package>` work out of the box inside the function.
echo ""
echo "⬇️   Installing '${PACKAGE_NAME}' into layer directory…"
mkdir -p "${SITE_PACKAGES_PATH}"
 
"${PIP_CMD}" install \
  "${PACKAGE_NAME}" \
  --target "${SITE_PACKAGES_PATH}" \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version "${PYTHON_VERSION}" \
  --only-binary=:all: \
  --upgrade \
  --quiet
 
echo "✅  Installation complete."
 
# ── Zip ───────────────────────────────────────────────────────────────────────
echo ""
echo "🗜   Creating zip archive…"
(
  cd "${LAYER_DIR}"
  zip -r "../${OUTPUT_ZIP}" . -x "*.pyc" -x "*/__pycache__/*" -x "*.dist-info/*"
)
 
ZIP_SIZE=$(du -sh "${OUTPUT_ZIP}" | cut -f1)
echo "✅  Created ${OUTPUT_ZIP} (${ZIP_SIZE})"
 
# ── Optional cleanup ──────────────────────────────────────────────────────────
rm -rf "${LAYER_DIR}"
