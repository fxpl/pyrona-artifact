#!/usr/bin/env bash

set -euo pipefail

BASELINE_REPO_DEFAULT="git@github.com:python/cpython.git"
PATCHED_REPO_DEFAULT="git@github.com:fxpl/cpython.git"
BASELINE_REF_DEFAULT="aeff92d86a3"
PATCHED_REF_DEFAULT="immutable-main"
OUTPUT_DIR_DEFAULT="snapshots"
MANIFEST_DEFAULT="$OUTPUT_DIR_DEFAULT/snapshot-manifest.json"
SOURCES_DEFAULT="$OUTPUT_DIR_DEFAULT/snapshot-sources.env"

BASELINE_REPO="$BASELINE_REPO_DEFAULT"
PATCHED_REPO="$PATCHED_REPO_DEFAULT"
BASELINE_REF="$BASELINE_REF_DEFAULT"
PATCHED_REF="$PATCHED_REF_DEFAULT"
OUTPUT_DIR="$OUTPUT_DIR_DEFAULT"
MANIFEST_PATH="$MANIFEST_DEFAULT"
SOURCES_PATH="$SOURCES_DEFAULT"
FORCE=1

SCRIPT_NAME="$(basename "$0")"

usage() {
  cat <<EOF
Usage: $SCRIPT_NAME [options]

Create vendored source snapshots for an artifact from:
  - baseline CPython (upstream)
  - patched CPython (fork)

Options:
  --baseline-repo <repo>    Baseline git remote URL
                            (default: $BASELINE_REPO_DEFAULT)
  --patched-repo <repo>     Patched git remote URL
                            (default: $PATCHED_REPO_DEFAULT)
  --baseline-ref <ref>      Baseline tag/branch/commit
                            (default: $BASELINE_REF_DEFAULT)
  --patched-ref <ref>       Patched tag/branch/commit
                            (default: $PATCHED_REF_DEFAULT)
  --output-dir <path>       Root directory for snapshots
                            (default: $OUTPUT_DIR_DEFAULT)
  --manifest <path>         JSON run manifest output path
                            (default: $MANIFEST_DEFAULT)
  --sources-file <path>     Env-style sources output path
                            (default: $SOURCES_DEFAULT)
  --no-force                Fail if snapshot directories already exist
  -h, --help                Show this help

Examples:
  $SCRIPT_NAME --baseline-ref 754e7c9b --patched-ref immutable-main
  $SCRIPT_NAME --baseline-ref 754e7c9b --patched-ref 7caa6ec
EOF
}

die() {
  echo "error: $*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

json_escape() {
  printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'
}

resolve_ref_to_commit() {
  local repo_dir="$1"
  local ref="$2"

  git -C "$repo_dir" rev-parse --verify "$ref^{commit}" 2>/dev/null \
    || git -C "$repo_dir" rev-parse --verify "refs/tags/$ref^{commit}" 2>/dev/null \
    || git -C "$repo_dir" rev-parse --verify "refs/heads/$ref^{commit}" 2>/dev/null \
    || git -C "$repo_dir" rev-parse --verify "refs/remotes/origin/$ref^{commit}" 2>/dev/null \
    || die "could not resolve ref '$ref' in repo '$repo_dir'"
}

to_abs_path() {
  local path="$1"

  if [ "${path#/}" != "$path" ]; then
    printf '%s\n' "$path"
    return
  fi

  local dir
  local base
  dir="$(dirname "$path")"
  base="$(basename "$path")"

  printf '%s/%s\n' "$(cd "$dir" && pwd -P)" "$base"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --baseline-repo)
      [ "$#" -ge 2 ] || die "missing value for $1"
      BASELINE_REPO="$2"
      shift 2
      ;;
    --patched-repo)
      [ "$#" -ge 2 ] || die "missing value for $1"
      PATCHED_REPO="$2"
      shift 2
      ;;
    --baseline-ref)
      [ "$#" -ge 2 ] || die "missing value for $1"
      BASELINE_REF="$2"
      shift 2
      ;;
    --patched-ref)
      [ "$#" -ge 2 ] || die "missing value for $1"
      PATCHED_REF="$2"
      shift 2
      ;;
    --output-dir)
      [ "$#" -ge 2 ] || die "missing value for $1"
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --manifest)
      [ "$#" -ge 2 ] || die "missing value for $1"
      MANIFEST_PATH="$2"
      shift 2
      ;;
    --sources-file)
      [ "$#" -ge 2 ] || die "missing value for $1"
      SOURCES_PATH="$2"
      shift 2
      ;;
    --no-force)
      FORCE=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown option: $1"
      ;;
  esac
done

require_cmd git
require_cmd mktemp
require_cmd sed
require_cmd tar

mkdir -p "$OUTPUT_DIR"
mkdir -p "$(dirname "$MANIFEST_PATH")"
mkdir -p "$(dirname "$SOURCES_PATH")"

OUTPUT_DIR="$(to_abs_path "$OUTPUT_DIR")"
MANIFEST_PATH="$(to_abs_path "$MANIFEST_PATH")"
SOURCES_PATH="$(to_abs_path "$SOURCES_PATH")"

BASELINE_DIR="$OUTPUT_DIR/cpython-baseline"
PATCHED_DIR="$OUTPUT_DIR/cpython-patched"

if [ "$FORCE" -eq 0 ]; then
  [ ! -e "$BASELINE_DIR" ] || die "$BASELINE_DIR exists; remove it or rerun without --no-force"
  [ ! -e "$PATCHED_DIR" ] || die "$PATCHED_DIR exists; remove it or rerun without --no-force"
fi

TMP_ROOT="$(mktemp -d -t cpython-snapshots-XXXXXX)"
cleanup() {
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

export_snapshot() {
  local name="$1"
  local repo="$2"
  local ref="$3"
  local target_dir="$4"
  local clone_dir="$TMP_ROOT/$name-repo"
  local commit

  echo "[info] cloning $name repo: $repo"
  git clone --no-checkout "$repo" "$clone_dir"

  echo "[info] resolving $name ref: $ref"
  commit="$(resolve_ref_to_commit "$clone_dir" "$ref")"

  if [ "$FORCE" -eq 1 ]; then
    rm -rf "$target_dir"
  fi
  mkdir -p "$target_dir"

  echo "[info] exporting $name snapshot to: $target_dir"
  git -C "$clone_dir" archive --format=tar "$commit" | tar -xf - -C "$target_dir"
}

export_snapshot "baseline" "$BASELINE_REPO" "$BASELINE_REF" "$BASELINE_DIR"
export_snapshot "patched" "$PATCHED_REPO" "$PATCHED_REF" "$PATCHED_DIR"

BASELINE_COMMIT="$(resolve_ref_to_commit "$TMP_ROOT/baseline-repo" "$BASELINE_REF")"
PATCHED_COMMIT="$(resolve_ref_to_commit "$TMP_ROOT/patched-repo" "$PATCHED_REF")"
BASELINE_DATE="$(git -C "$TMP_ROOT/baseline-repo" show -s --format=%cI "$BASELINE_COMMIT")"
PATCHED_DATE="$(git -C "$TMP_ROOT/patched-repo" show -s --format=%cI "$PATCHED_COMMIT")"
RUN_AT_UTC="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

{
  cat <<EOF
# Generated by $SCRIPT_NAME at $RUN_AT_UTC
BASELINE_REPO=$BASELINE_REPO
BASELINE_REF=$BASELINE_REF
BASELINE_COMMIT=$BASELINE_COMMIT
PATCHED_REPO=$PATCHED_REPO
PATCHED_REF=$PATCHED_REF
PATCHED_COMMIT=$PATCHED_COMMIT
EOF

  cat <<'EOF'

# Resolve snapshot paths from this env file location so the file is portable
# across host and container workspaces. Callers can still override any path.
_SNAPSHOT_SOURCES_DIR="$(
  cd "$(dirname "${BASH_SOURCE[0]:-${0}}")" \
  && pwd -P
)"
SNAPSHOT_OUTPUT_DIR="${SNAPSHOT_OUTPUT_DIR:-${_SNAPSHOT_SOURCES_DIR}}"
BASELINE_PYTHON_DIR="${BASELINE_PYTHON_DIR:-${SNAPSHOT_OUTPUT_DIR}/cpython-baseline}"
PATCHED_PYTHON_DIR="${PATCHED_PYTHON_DIR:-${SNAPSHOT_OUTPUT_DIR}/cpython-patched}"
BASELINE_PYTHON_BIN="${BASELINE_PYTHON_BIN:-${BASELINE_PYTHON_DIR}/python}"
PATCHED_PYTHON_BIN="${PATCHED_PYTHON_BIN:-${PATCHED_PYTHON_DIR}/python}"

unset _SNAPSHOT_SOURCES_DIR
EOF
} > "$SOURCES_PATH"

cat > "$MANIFEST_PATH" <<EOF
{
  "generated_at_utc": "$(json_escape "$RUN_AT_UTC")",
  "script": "$(json_escape "$SCRIPT_NAME")",
  "snapshots": {
    "baseline": {
      "repo": "$(json_escape "$BASELINE_REPO")",
      "requested_ref": "$(json_escape "$BASELINE_REF")",
      "resolved_commit": "$(json_escape "$BASELINE_COMMIT")",
      "commit_date": "$(json_escape "$BASELINE_DATE")",
      "export_path": "$(json_escape "$BASELINE_DIR")"
    },
    "patched": {
      "repo": "$(json_escape "$PATCHED_REPO")",
      "requested_ref": "$(json_escape "$PATCHED_REF")",
      "resolved_commit": "$(json_escape "$PATCHED_COMMIT")",
      "commit_date": "$(json_escape "$PATCHED_DATE")",
      "export_path": "$(json_escape "$PATCHED_DIR")"
    }
  }
}
EOF

cat <<EOF
[done] snapshots created
  baseline: $BASELINE_DIR ($BASELINE_COMMIT)
  patched:  $PATCHED_DIR ($PATCHED_COMMIT)
  sources:  $SOURCES_PATH
  manifest: $MANIFEST_PATH
EOF
