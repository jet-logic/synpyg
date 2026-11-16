#!/usr/bin/env bash
set -euo pipefail
PATCH_FILE="${1:-.vscode/now.patch}"

patch --dry-run --batch -p1 < "$PATCH_FILE" \
  && patch --batch -p1 < "$PATCH_FILE" \
  && echo "Applied $PATCH_FILE"