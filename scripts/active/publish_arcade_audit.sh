#!/bin/bash
set -euo pipefail

PUBLISHER='/userdata/system/el_gordo_tools/publish_arcade_audit_github.py'
PYTHON='/usr/bin/python3'
DRY_RUN=0
ONE_TIME=0

if [[ "${1:-}" == '--dry-run' ]]; then
    DRY_RUN=1
    shift
fi
if [[ "${1:-}" == '--one-time-approved' ]]; then
    ONE_TIME=1
    shift
fi
if [[ $# -ne 1 || -z "$1" ]]; then
    printf '%s\n' 'Uso: publish_arcade_audit.sh [--dry-run] [--one-time-approved] "descripcion"' >&2
    exit 2
fi
MESSAGE="$1"

if [[ ! -x "$PYTHON" || ! -f "$PUBLISHER" ]]; then
    printf '%s\n' 'PUBLISHER_NOT_AVAILABLE'
    exit 2
fi

# This wrapper is the explicit human/Codex decision point. It is never called
# automatically by boot hooks or game launchers.
"$PYTHON" "$PUBLISHER" --sync-export
if [[ "$ONE_TIME" -eq 1 ]]; then
    "$PYTHON" "$PUBLISHER" --dry-run --one-time-approved --message "$MESSAGE"
else
    "$PYTHON" "$PUBLISHER" --dry-run --message "$MESSAGE"
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
    exit 0
fi

# The explicit wrapper invocation authorizes this publisher-only operation.
# The Python program still requires and checks the internal allow-publish flag.
if [[ "$ONE_TIME" -eq 1 ]]; then
    "$PYTHON" "$PUBLISHER" --allow-publish --one-time-approved --message "$MESSAGE"
else
    "$PYTHON" "$PUBLISHER" --allow-publish --message "$MESSAGE"
fi
