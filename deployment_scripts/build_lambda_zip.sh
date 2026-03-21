#!/bin/bash
set -euo pipefail

# Usage: ./package_lambda.sh <dir1> <dir2> ... <dirN>
#
# For each directory:
#   1. Installs dependencies from requirements.txt (if present)
#   2. Packages all .py files into {directory_name}-lambda.zip
#   3. Uploads the zip to s3://$S3_BUCKET-east-<account> and s3://$S3_BUCKET-west-<account>
#
# Required environment variables:
#   S3_BUCKET       - S3 bucket base name
#                     e.g. S3_BUCKET=my-artifacts -> my-artifacts-east-123456789012, my-artifacts-west-123456789012
#   AWS_ACCOUNT_ID  - AWS account number appended after the region suffix

REGIONS=("us-east-1" "us-west-2")

region_suffix() {
    case "$1" in
        us-east-1) echo "east" ;;
        us-west-2) echo "west" ;;
        *) echo "Error: unknown region '$1'" >&2; exit 1 ;;
    esac
}

# ── Validation ────────────────────────────────────────────────────────────────
if [[ $# -eq 0 ]]; then
    echo "Error: at least one Lambda directory is required."
    echo "Usage: $0 <dir1> <dir2> ... <dirN>"
    exit 1
fi

if [[ -z "${S3_BUCKET:-}" ]]; then
    echo "Error: S3_BUCKET environment variable is not set."
    exit 1
fi

if [[ -z "${AWS_ACCOUNT_ID:-}" ]]; then
    echo "Error: AWS_ACCOUNT_ID environment variable is not set."
    exit 1
fi

OUTPUT_DIR="$(mktemp -d)"
trap 'rm -rf "$OUTPUT_DIR"' EXIT

FAILED=()

for SOURCE_DIR in "$@"; do
    if [[ ! -d "$SOURCE_DIR" ]]; then
        echo "Warning: '$SOURCE_DIR' is not a directory, skipping."
        FAILED+=("$SOURCE_DIR (not a directory)")
        continue
    fi

    FUNCTION_NAME="$(basename "$SOURCE_DIR")"
    ZIP_NAME="${FUNCTION_NAME}-lambda.zip"
    BUILD_DIR="$(mktemp -d)"
    ZIP_PATH="$OUTPUT_DIR/$ZIP_NAME"

    echo "──────────────────────────────────────────────"
    echo "==> Function : $FUNCTION_NAME"
    echo "    Source   : $SOURCE_DIR"
    echo "    Output   : $ZIP_NAME"

    # 1. Install dependencies
    if [[ -f "$SOURCE_DIR/requirements.txt" ]]; then
        echo "    Installing dependencies..."
        pipenv run pip install \
            --quiet \
            --requirement "$SOURCE_DIR/requirements.txt" \
            --target "$BUILD_DIR" \
            --upgrade \
            --no-cache-dir
    else
        echo "    No requirements.txt found, skipping dependency install."
    fi

    # 2. Copy .py files
    echo "    Copying Python source files..."
    find "$SOURCE_DIR" -maxdepth 1 -name "*.py" | while read -r pyfile; do
        cp "$pyfile" "$BUILD_DIR/"
    done

    # 3. Zip
    (cd "$BUILD_DIR" && zip -r9 -q "$ZIP_PATH" .)
    rm -rf "$BUILD_DIR"
    echo "    Packaged: $ZIP_NAME ($(du -sh "$ZIP_PATH" | cut -f1))"

    # 4. Upload to each region
    for REGION in "${REGIONS[@]}"; do
        S3_URI="s3://${S3_BUCKET}-$(region_suffix "$REGION")-${AWS_ACCOUNT_ID}/lambda-code-artifacts/${ZIP_NAME}"
        echo "    Uploading to $S3_URI ..."
        if aws s3 cp "$ZIP_PATH" "$S3_URI" --region "$REGION" --no-progress; then
            echo "    ✓ $REGION"
        else
            echo "    ✗ Upload failed: $S3_URI"
            FAILED+=("$FUNCTION_NAME (upload $REGION)")
        fi
    done
done

echo ""
echo "══════════════════════════════════════════════"
if [[ ${#FAILED[@]} -gt 0 ]]; then
    echo "✗ Completed with errors:"
    for f in "${FAILED[@]}"; do
        echo "    - $f"
    done
    exit 1
else
    echo "✓ All Lambda functions packaged and uploaded successfully."
fi