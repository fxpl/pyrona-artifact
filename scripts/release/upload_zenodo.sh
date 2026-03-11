#!/usr/bin/env bash

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"

usage() {
    cat <<EOF
Usage: $SCRIPT_NAME <artifacts-dir>

Upload files from a local directory tree into an existing Zenodo draft deposition.
The relative directory structure under <artifacts-dir> is preserved.

Options:
    -h, --help               Show this help

Environment:
    ZENODO_TOKEN             Zenodo personal access token
    ZENODO_DEPOSITION_ID     Existing draft deposition id
EOF
}

die() {
    echo "error: $*" >&2
    exit 1
}

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

API_URL="https://zenodo.org/api"

print_api_error() {
    local response_file="$1"

    [ -s "$response_file" ] || return 0

    python3 - "$response_file" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, 'r', encoding='utf-8') as fh:
    body = fh.read().strip()

if not body:
    raise SystemExit(0)

try:
    payload = json.loads(body)
except json.JSONDecodeError:
    print(body, file=sys.stderr)
    raise SystemExit(0)

message = payload.get('message')
status = payload.get('status')
if message or status:
    prefix = 'Zenodo API error'
    if status is not None:
        prefix += f' ({status})'
    if message:
        prefix += f': {message}'
    print(prefix, file=sys.stderr)

for error in payload.get('errors', []):
    field = error.get('field')
    detail = error.get('message', '')
    if field:
        print(f'  - {field}: {detail}', file=sys.stderr)
    elif detail:
        print(f'  - {detail}', file=sys.stderr)
PY
}

api_request() {
    local method="$1"
    local url="$2"
    local data_file="${3:-}"
    local response_file
    local http_code
    local curl_status

    response_file="$(mktemp "$tmp_dir/curl-response.XXXXXX")"

    if [ -n "$data_file" ]; then
        http_code="$(curl --silent --show-error \
            --output "$response_file" \
            --write-out '%{http_code}' \
            --request "$method" \
            --header "Authorization: Bearer $ZENODO_TOKEN" \
            --header "Content-Type: application/json" \
            --header "Accept: application/json" \
            --data-binary "@$data_file" \
            "$url")" || {
            curl_status=$?
            print_api_error "$response_file"
            rm -f "$response_file"
            exit "$curl_status"
        }
    else
        http_code="$(curl --silent --show-error \
            --output "$response_file" \
            --write-out '%{http_code}' \
            --request "$method" \
            --header "Authorization: Bearer $ZENODO_TOKEN" \
            --header "Accept: application/json" \
            "$url")" || {
            curl_status=$?
            print_api_error "$response_file"
            rm -f "$response_file"
            exit "$curl_status"
        }
    fi

    if [ "$http_code" -ge 400 ]; then
        echo "error: Zenodo API request failed with HTTP $http_code" >&2
        print_api_error "$response_file"
        rm -f "$response_file"
        exit 1
    fi

    cat "$response_file"
    rm -f "$response_file"
}

api_delete_file() {
    local url="$1"
    local response_file
    local http_code
    local curl_status

    response_file="$(mktemp "$tmp_dir/curl-response.XXXXXX")"
    http_code="$(curl --silent --show-error \
        --output "$response_file" \
        --write-out '%{http_code}' \
        --request DELETE \
        --header "Authorization: Bearer $ZENODO_TOKEN" \
        --header "Accept: application/json" \
        "$url")" || {
        curl_status=$?
        print_api_error "$response_file"
        rm -f "$response_file"
        exit "$curl_status"
    }

    if [ "$http_code" -ge 400 ]; then
        echo "error: Zenodo file delete failed with HTTP $http_code" >&2
        print_api_error "$response_file"
        rm -f "$response_file"
        exit 1
    fi

    rm -f "$response_file"
}

api_upload_file() {
    local file_path="$1"
    local url="$2"
    local response_file
    local http_code
    local curl_status

    response_file="$(mktemp "$tmp_dir/curl-response.XXXXXX")"
    http_code="$(curl --silent --show-error \
        --output "$response_file" \
        --write-out '%{http_code}' \
        --request PUT \
        --header "Authorization: Bearer $ZENODO_TOKEN" \
        --header "Content-Type: application/octet-stream" \
        --upload-file "$file_path" \
        "$url")" || {
        curl_status=$?
        print_api_error "$response_file"
        rm -f "$response_file"
        exit "$curl_status"
    }

    if [ "$http_code" -ge 400 ]; then
        echo "error: Zenodo file upload failed with HTTP $http_code" >&2
        print_api_error "$response_file"
        rm -f "$response_file"
        exit 1
    fi

    rm -f "$response_file"
}

ARTIFACTS_DIR=""
DEPOSITION_ID="${ZENODO_DEPOSITION_ID:-}"

while [ "$#" -gt 0 ]; do
    case "$1" in
        -h|--help)
            usage
            exit 0
            ;;
        -*)
            die "unknown option: $1"
            ;;
        *)
            [ -z "$ARTIFACTS_DIR" ] || die "unexpected argument: $1"
            ARTIFACTS_DIR="$1"
            shift
            ;;
    esac
done

[ -n "${ZENODO_TOKEN:-}" ] || die "ZENODO_TOKEN is undefined"
[ -n "$ARTIFACTS_DIR" ] || die "provide the artifacts directory as the only argument"
[ -d "$ARTIFACTS_DIR" ] || die "artifacts directory does not exist: $ARTIFACTS_DIR"
[ -n "$DEPOSITION_ID" ] || die "ZENODO_DEPOSITION_ID is undefined"

require_cmd curl
require_cmd python3

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

artifact_count="$(find "$ARTIFACTS_DIR" -type f | wc -l | tr -d ' ')"
[ "$artifact_count" -gt 0 ] || die "no files found in artifacts directory: $ARTIFACTS_DIR"

echo "[info] using Zenodo deposition id: $DEPOSITION_ID"

deposition_json="$tmp_dir/deposition.json"
api_request GET "$API_URL/deposit/depositions/$DEPOSITION_ID" > "$deposition_json"

bucket_url="$(python3 - "$deposition_json" <<'PY'
import json
import sys

with open(sys.argv[1], 'r', encoding='utf-8') as fh:
    payload = json.load(fh)

print(payload.get('links', {}).get('bucket', ''))
PY
)"
[ -n "$bucket_url" ] || die "Zenodo deposition does not expose a bucket URL"

existing_files_tsv="$tmp_dir/existing-files.tsv"
python3 - "$deposition_json" > "$existing_files_tsv" <<'PY'
import json
import sys

with open(sys.argv[1], 'r', encoding='utf-8') as fh:
    payload = json.load(fh)

for file_info in payload.get('files', []):
    print(f"{file_info['filename']}\t{file_info['links']['self']}")
PY

while IFS= read -r -d '' artifact_path; do
    artifact_name="${artifact_path#"$ARTIFACTS_DIR"/}"

    while IFS=$'\t' read -r existing_name existing_url; do
        [ -n "$existing_name" ] || continue
        if [ "$existing_name" = "$artifact_name" ]; then
            echo "[info] removing existing Zenodo file: $artifact_name"
            api_delete_file "$existing_url"
        fi
    done < "$existing_files_tsv"

    quoted_name="$(python3 - "$artifact_name" <<'PY'
import sys
import urllib.parse

print(urllib.parse.quote(sys.argv[1]))
PY
)"

    echo "[info] uploading $artifact_name"
    api_upload_file "$artifact_path" "$bucket_url/$quoted_name"
done < <(find "$ARTIFACTS_DIR" -type f -print0)

echo "[done] Zenodo upload completed for deposition: $DEPOSITION_ID"
