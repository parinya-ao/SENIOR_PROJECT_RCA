#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.."
if [[ -z ${CPP_QUALITY_PYTHON:-} && -x .venv/bin/python ]]; then
  CPP_QUALITY_PYTHON=.venv/bin/python
fi
exec "${CPP_QUALITY_PYTHON:-python3}" scripts/quality/check_cpp.py "$@"
