#!/usr/bin/env bash
# Source-local Git Bash entrypoint for the single reviewed Python research lab.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if command -v py >/dev/null 2>&1; then PY=(py -3); elif command -v python3 >/dev/null 2>&1; then PY=(python3); else PY=(python); fi
usage() {
  cat <<'HELP'
Usage: bash scripts/golf.sh <command> [arguments]
  sync                 Safely fast-forward clean main from approved GitHub origin
  list                 Show registered experiments and merged agent tests
  plan ID [flags]      Review an experiment without executing it
  run ID [flags]       Run one offline test; live requires --live and human consent
  history              Inspect local run metadata (not game scores)
  reports              Show sanitized local observations
  test [flags]         Run offline regression tests
  doctor               Diagnose local setup, without opening Dolphin
  <other> [flags]      Forward to canonical scripts/golf.py CLI
No script uploads raw RAM, ROMs, savestates, screenshots or credentials.
Agent commits and reviewed PRs are the GitHub publishing path.
HELP
}
case "${1:-help}" in
  help|-h|--help) usage;;
  sync) shift; exec "${PY[@]}" scripts/golf.py lab sync "$@";;
  list) shift; exec "${PY[@]}" scripts/golf.py lab list "$@";;
  plan|run|history|reports) cmd="$1"; shift; exec "${PY[@]}" scripts/golf.py lab "$cmd" "$@";;
  *) exec "${PY[@]}" scripts/golf.py "$@";;
esac
