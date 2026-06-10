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
PIDS=()

# Function to process a single Lambda directory
process_lambda() {
    local SOURCE_DIR="$1"
    local OUTPUT_DIR="$2"
    local S3_BUCKET="$3"
    local AWS_ACCOUNT_ID="$4"

    if [[ ! -d "$SOURCE_DIR" ]]; then
        echo "Warning: '$SOURCE_DIR' is not a directory, skipping."
        echo "$SOURCE_DIR (not a directory)" >> "$OUTPUT_DIR/failed.txt"
        return 1
    fi

    FUNCTION_NAME="$(basename "$SOURCE_DIR")"
    ZIP_NAME="${FUNCTION_NAME}-lambda.zip"
    ZIP_PATH="$OUTPUT_DIR/$ZIP_NAME"
    KEY="lambda-code-artifacts/${ZIP_NAME}"

    # Content hash of the build inputs: this function's source dir (which includes its
    # handler + requirements.txt) and the vendored shared common/ package. Computed from
    # the committed git tree objects, so it changes only when a file inside changes.
    local DIR_PATH="${SOURCE_DIR#./}"
    local SRC_HASH
    SRC_HASH="$( { git rev-parse "HEAD:$DIR_PATH"; git rev-parse "HEAD:src/common"; } \
        | sha256sum | cut -c1-12 )"

    echo "──────────────────────────────────────────────"
    echo "==> Function : $FUNCTION_NAME"
    echo "    Source   : $SOURCE_DIR"
    echo "    Output   : $ZIP_NAME"
    echo "    Hash     : $SRC_HASH"

    # Skip any region whose existing artifact already carries this source hash. Because
    # the Lambda tracks the S3 object version, not re-uploading means no new version and
    # therefore no redeploy of unchanged code.
    local REGIONS_TO_UPLOAD=()
    for REGION in "${REGIONS[@]}"; do
        local BUCKET="${S3_BUCKET}-$(region_suffix "$REGION")-${AWS_ACCOUNT_ID}"
        local EXISTING
        EXISTING="$(aws s3api head-object --bucket "$BUCKET" --key "$KEY" \
            --region "$REGION" --query 'Metadata."source-hash"' --output text 2>/dev/null || echo "")"
        if [[ "$EXISTING" == "$SRC_HASH" ]]; then
            echo "    ✓ $REGION already up to date (hash $SRC_HASH) — skipping"
        else
            REGIONS_TO_UPLOAD+=("$REGION")
        fi
    done

    if [[ ${#REGIONS_TO_UPLOAD[@]} -eq 0 ]]; then
        echo "    No source changes — nothing to package or upload for $FUNCTION_NAME."
        return 0
    fi

    BUILD_DIR="$(mktemp -d)"

    # 1. Install dependencies
    if [[ -f "$SOURCE_DIR/requirements.txt" ]]; then
        echo "    Installing dependencies..."
        pip install \
            --quiet \
            --requirement "$SOURCE_DIR/requirements.txt" \
            --target "$BUILD_DIR" \
            --upgrade \
            --no-cache-dir
    else
        echo "    No requirements.txt found, skipping dependency install."
    fi

    # 2. Copy .py files and config
    echo "    Copying Python source files..."
    find "$SOURCE_DIR" -maxdepth 1 -name "*.py" | while read -r pyfile; do
        cp "$pyfile" "$BUILD_DIR/"
    done

    # Copy the shared common package (vendored into every function zip so
    # ``import common.*`` resolves at runtime).
    COMMON_DIR="$(dirname "$SOURCE_DIR")/common"
    if [[ -d "$COMMON_DIR" ]]; then
        echo "    Copying shared common package..."
        cp -R "$COMMON_DIR" "$BUILD_DIR/"
        rm -rf "$BUILD_DIR/common/__pycache__"
    fi

    # Copy the OTEL collector config
    if [[ -f "$SOURCE_DIR/otel-collector-config.yaml" ]]; then
        cp "$SOURCE_DIR/otel-collector-config.yaml" "$BUILD_DIR/"
    fi

    # 3. Zip
    (cd "$BUILD_DIR" && zip -r9 -q "$ZIP_PATH" .)
    rm -rf "$BUILD_DIR"
    echo "    Packaged: $ZIP_NAME ($(du -sh "$ZIP_PATH" | cut -f1))"

    # 4. Upload (in parallel) only to the regions that need it, stamping the source hash
    #    as object metadata so the next run can tell whether anything changed.
    UPLOAD_PIDS=()
    for REGION in "${REGIONS_TO_UPLOAD[@]}"; do
        (
            S3_URI="s3://${S3_BUCKET}-$(region_suffix "$REGION")-${AWS_ACCOUNT_ID}/${KEY}"
            echo "    Uploading to $S3_URI ..."
            if aws s3 cp "$ZIP_PATH" "$S3_URI" --region "$REGION" --no-progress \
                 --metadata "source-hash=$SRC_HASH"; then
                echo "    ✓ $REGION"
            else
                echo "    ✗ Upload failed: $S3_URI"
                echo "$FUNCTION_NAME (upload $REGION)" >> "$OUTPUT_DIR/failed.txt"
            fi
        ) &
        UPLOAD_PIDS+=($!)
    done

    # Wait for all uploads to complete
    for pid in "${UPLOAD_PIDS[@]}"; do
        wait $pid
    done
}

# Process all Lambda directories in parallel
for SOURCE_DIR in "$@"; do
    process_lambda "$SOURCE_DIR" "$OUTPUT_DIR" "$S3_BUCKET" "$AWS_ACCOUNT_ID" &
    PIDS+=($!)
done

# Wait for all Lambda processing to complete
for pid in "${PIDS[@]}"; do
    wait $pid
done

# Collect failures from the failed.txt file
if [[ -f "$OUTPUT_DIR/failed.txt" ]]; then
    while IFS= read -r line; do
        FAILED+=("$line")
    done < "$OUTPUT_DIR/failed.txt"
fi

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