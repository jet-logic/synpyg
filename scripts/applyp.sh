#!/usr/bin/env bash
set -euo pipefail

TAG="${1:-project}"
DIR=/tmp/$TAG
DONE="$DIR/done"
PATCH_FILE="$DIR/now.patch"

if [ ! -f "$PATCH_FILE" ]; then
    mkdir -p "$DIR"
    ln -vsfn "$DIR/not" "$PATCH_FILE"
fi 
LINK="$PATCH_FILE"
if [ -L "$LINK" ]; then
  if [ ! -e "$LINK" ]; then
      printf "Symlink target does not exist.\nEnter a new file path: "
      read -r NEW_TARGET
      if [ -e "$NEW_TARGET" ]; then
          ln -vsfn "$NEW_TARGET" "$LINK"
      else
          echo "Error: '$NEW_TARGET' does not exist." >&2
          exit 1
      fi
  fi
fi


if [ -f "$PATCH_FILE" ]; then
    mkdir -p "$DONE"
    patch --dry-run -p1 < "$PATCH_FILE" \
        && patch -p1 < "$PATCH_FILE" \
        && echo "Applied $PATCH_FILE" && mv -vft "$DONE" "$(readlink -f "$PATCH_FILE")"
fi