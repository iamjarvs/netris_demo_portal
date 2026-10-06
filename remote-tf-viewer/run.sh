#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="python3"

# Use repo virtualenv if available
if [ -f "$DIR/../demo-portal/.venv/bin/python3" ]; then
    PYTHON_BIN="$DIR/../demo-portal/.venv/bin/python3"
fi

exec "$PYTHON_BIN" "$DIR/open_tf.py" "$@"
