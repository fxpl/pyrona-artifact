#!/usr/bin/env bash

set -euo pipefail

rm -rf uv/snapshots/uv.lock
rm -rf uv/stable/uv.lock

scripts/setup/2_build_venv.sh --no-frozen
