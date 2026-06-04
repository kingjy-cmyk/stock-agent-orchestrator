#!/usr/bin/env sh
set -eu

VENV_PATH="${1:-.venv}"

if [ ! -d "$VENV_PATH" ]; then
  python3 -m venv "$VENV_PATH"
fi

"$VENV_PATH/bin/python" -m pip install --upgrade pip
"$VENV_PATH/bin/python" -m pip install -e .
"$VENV_PATH/bin/python" -m stock_agent_orchestrator.cli doctor
"$VENV_PATH/bin/python" -m stock_agent_orchestrator.cli demo

echo "bootstrap complete"
