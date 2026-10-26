#!/usr/bin/env bash
# Regenerate references/api-index.md from the live Rocket.Chat OpenAPI spec.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=rc-common.sh
. "$SCRIPT_DIR/rc-common.sh"

out="$SKILL_DIR/references/api-index.md"

while (($#)); do
  case "$1" in
    --out)
      out="${2:-}"
      shift 2
      ;;
    --out=*)
      out="${1#*=}"
      shift
      ;;
    -h|--help)
      cat <<'EOF'
Usage: rc-index.sh [--out FILE]

Fetches both the documented and full (withUndocumented) live specs,
then writes a grouped markdown index. Undocumented routes are marked with †.
EOF
      exit 0
      ;;
    *)
      printf 'ERROR: Unknown argument: %s\n' "$1" >&2
      exit 2
      ;;
  esac
done

full_spec="$(rc_fetch_spec full)" || exit 1
doc_spec="$(rc_fetch_spec doc)" || doc_spec=""

rc_optional_env
url="${RC_URL%/}/api/docs/json"

if [[ -n "$doc_spec" ]]; then
  python3 "$SCRIPT_DIR/rc_spec.py" index \
    --spec "$full_spec" \
    --doc-spec "$doc_spec" \
    --out "$out" \
    --url "$url"
else
  python3 "$SCRIPT_DIR/rc_spec.py" index \
    --spec "$full_spec" \
    --out "$out" \
    --url "$url"
fi

printf 'Wrote %s\n' "$out"
