#!/usr/bin/env bash
# One-command demo runner for the Research Agent live session.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "Installing dependencies..."
pip install -q -r requirements.txt

# .env always wins — overrides a stale shell export (e.g. pasted placeholder).
if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo ""
  echo "ERROR: OPENAI_API_KEY is not set."
  echo ""
  echo "Edit .env in this folder and set your real key:"
  echo "  OPENAI_API_KEY=sk-..."
  echo ""
  echo "Copy .env.example to .env if you need a template:"
  echo "  cp .env.example .env"
  echo ""
  echo "Then run again:"
  echo "  ./run_demo.sh"
  exit 1
fi

# Catch common placeholder values before hitting the API.
if [[ "${OPENAI_API_KEY}" == *"PASTE"* ]] \
  || [[ "${OPENAI_API_KEY}" == *"your-real-key"* ]] \
  || [[ "${OPENAI_API_KEY}" == *"your-key"* ]] \
  || [[ "${OPENAI_API_KEY}" == sk-your-* ]] \
  || [[ "${#OPENAI_API_KEY}" -lt 40 ]]; then
  echo ""
  echo "ERROR: OPENAI_API_KEY in .env is still a placeholder."
  echo ""
  echo "Open .env and replace it with your real key from:"
  echo "  https://platform.openai.com/account/api-keys"
  echo ""
  echo "Do NOT run the echo command from demo-script.txt — edit .env directly."
  exit 1
fi

MODE="${1:-main}"

case "$MODE" in
  main)
    echo ""
    echo "=== BEAT 1: Main demo (tool chaining) ==="
    python demo.py "What is 30% of New Zealand's population?"
    ;;
  direct)
    echo ""
    echo "=== OPTIONAL: Direct answer (no tools) ==="
    python demo.py --direct "Explain what an agent is in one line"
    ;;
  trace)
    echo ""
    echo "=== BEAT 3: Under the hood (raw observability trace) ==="
    python demo.py --trace "What is 30% of New Zealand's population?"
    ;;
  multi)
    echo ""
    echo "=== BEAT 4: Multi-agent handovers (orchestrator + workers) ==="
    python demo_multi.py
    ;;
  both)
    echo ""
    echo "=== BEAT 1: Main demo (tool chaining) ==="
    python demo.py "What is 30% of New Zealand's population?"
    echo ""
    echo "=== OPTIONAL: Direct answer (no tools) ==="
    python demo.py --direct "Explain what an agent is in one line"
    ;;
  *)
    echo "Usage: ./run_demo.sh [main|direct|trace|multi|both]"
    echo ""
    echo "  main   — default demo question (chains web_search + calculator)"
    echo "  direct — optional second run (model answers without tools)"
    echo "  trace  — pretty view + compact message trace for observability beat"
    echo "  multi  — multi-agent demo with orchestrator handovers"
    echo "  both   — run main then direct"
    exit 1
    ;;
esac
