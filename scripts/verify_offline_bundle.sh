#!/usr/bin/env bash
# Verify offline_bundle files against offline_data_manifest.txt
# Usage: ./scripts/verify_offline_bundle.sh [path-to-offline_bundle]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUNDLE="${1:-$ROOT/offline_bundle}"
MANIFEST="$ROOT/offline_data_manifest.txt"
fail=0
while IFS= read -r line; do
  [[ "$line" =~ ^# ]] && continue
  [[ -z "${line// }" ]] && continue
  hash=$(echo "$line" | awk '{print $1}')
  rel=$(echo "$line" | awk '{print $2}')
  path="$BUNDLE/$rel"
  if [[ ! -f "$path" ]]; then
    echo "MISSING: $path"
    fail=1
    continue
  fi
  got=$(sha256sum "$path" | awk '{print $1}')
  if [[ "$got" != "$hash" ]]; then
    echo "HASH MISMATCH: $rel"
    fail=1
  else
    echo "OK  $rel"
  fi
done < "$MANIFEST"
if [[ $fail -ne 0 ]]; then exit 1
fi
echo "All bundle files verified."
