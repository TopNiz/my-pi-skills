#!/usr/bin/env bash
# Describe one live Rocket.Chat API endpoint, or list a family.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=rc-common.sh
. "$SCRIPT_DIR/rc-common.sh"

usage() {
  cat <<'EOF'
Usage:
  rc-doc.sh <family>.<action> [--json]
  rc-doc.sh <METHOD> <path> [--json]
  rc-doc.sh --family <family>
  rc-doc.sh --list
  rc-doc.sh --documented-only ...

Examples:
  rc-doc.sh channels.create
  rc-doc.sh users.list
  rc-doc.sh POST /api/v1/channels.archive
  rc-doc.sh --family roles
  rc-doc.sh --list

By default the full live spec is used, including undocumented routes.
Use --documented-only to hide routes tagged "Missing Documentation".
EOF
}

full=1
declare -a passthrough=()
for arg in "$@"; do
  case "$arg" in
    --documented-only)
      full=0
      ;;
    --with-undocumented)
      full=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      passthrough+=("$arg")
      ;;
  esac
done

if [[ "$full" == "1" ]]; then
  spec="$(rc_fetch_spec full)" || exit 1
  doc_spec="$(rc_fetch_spec doc)" || doc_spec=""
else
  spec="$(rc_fetch_spec doc)" || exit 1
  doc_spec=""
fi

if [[ -n "$doc_spec" ]]; then
  exec python3 "$SCRIPT_DIR/rc_spec.py" doc --spec "$spec" --doc-spec "$doc_spec" "${passthrough[@]:-}"
fi
exec python3 "$SCRIPT_DIR/rc_spec.py" doc --spec "$spec" "${passthrough[@]:-}"
