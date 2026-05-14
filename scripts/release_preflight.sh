#!/usr/bin/env bash
# Проверка релизной воспроизводимости перед production deploy.
# Использование:
#   bash scripts/release_preflight.sh
#   bash scripts/release_preflight.sh <expected_commit>
#   RELEASE_COMMIT=<expected_commit> bash scripts/release_preflight.sh
set -euo pipefail

EXPECTED_COMMIT="${1:-${RELEASE_COMMIT:-}}"

HEAD_COMMIT="$(git rev-parse HEAD)"
STATUS_OUTPUT="$(git status --short)"

echo "git rev-parse HEAD"
echo "$HEAD_COMMIT"
echo

echo "git status --short"
if [[ -n "$STATUS_OUTPUT" ]]; then
  echo "$STATUS_OUTPUT"
else
  echo "(clean)"
fi
echo

echo "git log --oneline -5"
git log --oneline -5
echo

if [[ -n "$EXPECTED_COMMIT" && "$HEAD_COMMIT" != "$EXPECTED_COMMIT" ]]; then
  echo "ERROR: HEAD ($HEAD_COMMIT) does not match expected release commit ($EXPECTED_COMMIT)." >&2
  exit 1
fi

if [[ -n "$STATUS_OUTPUT" ]]; then
  echo "ERROR: working tree is dirty. Commit/stash/remove changes before deploy." >&2
  exit 1
fi

echo "Release preflight OK."
