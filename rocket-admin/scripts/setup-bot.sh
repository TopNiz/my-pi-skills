#!/usr/bin/env bash
# One-time setup: create a dedicated Rocket.Chat admin bot and write .env.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=rc-common.sh
. "$SCRIPT_DIR/rc-common.sh"

: "${RC_URL:=$RC_DEFAULT_URL}"
: "${RC_BOT_USERNAME:=rocket-admin-bot}"
: "${RC_BOT_EMAIL:=rocket-admin-bot@codimeo.com}"
: "${RC_BOT_NAME:=Rocket Admin Bot}"

force=0
if [[ "${1:-}" == "--force" ]]; then
  force=1
elif [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage: setup-bot.sh [--force]

Creates or updates a dedicated admin bot, generates a personal access token,
and writes the skill-local .env. Requires a one-time admin credential.

Admin credential sources, in order:
  1. RC_ADMIN_USER_ID and RC_ADMIN_TOKEN environment variables
  2. RC_ADMIN_ENV file (default: ~/.rocket-admin-setup.env)

Create the admin token in Rocket.Chat:
  Click your account profile icon, then Profile > Personal Access Tokens
  (direct URL: https://rocket.codimeo.com/account/tokens)

  Enter a name, choose "Ignore Two Factor Authentication", click "Add",
  verify with your password or 2FA code if prompted, then copy the user ID
  and access token from the success dialog. The token is shown only once.

The admin token is used only during this script and is never written to .env.
EOF
  exit 0
fi

rc_require_runtime || exit 1
rc_require_jq || exit 1

# Verify an existing .env before doing anything unless --force is used.
if [[ "$force" == "0" && -r "$RC_ENV_FILE" ]]; then
  if rc_load_env >/dev/null 2>&1; then
    check="$(curl -sS -m 20 \
      -H "X-User-Id: ${RC_USER_ID}" \
      -H "X-Auth-Token: ${RC_AUTH_TOKEN}" \
      "${RC_URL%/}/api/v1/me" 2>/dev/null || true)"
    if [[ "$(jq -r '.success // false' <<<"$check" 2>/dev/null)" == "true" ]]; then
      printf 'OK: existing .env already works. Use --force to reconfigure.\n'
      jq -r '"  user: \(.username)  roles: \(.roles | join(","))"' <<<"$check"
      exit 0
    fi
  fi
fi

admin_env="${RC_ADMIN_ENV:-$HOME/.rocket-admin-setup.env}"
if [[ -z "${RC_ADMIN_USER_ID:-}" || -z "${RC_ADMIN_TOKEN:-}" ]]; then
  if [[ -r "$admin_env" ]]; then
    set -a
    # shellcheck disable=SC1090
    . "$admin_env"
    set +a
  fi
fi

if [[ -z "${RC_ADMIN_USER_ID:-}" || -z "${RC_ADMIN_TOKEN:-}" ]]; then
  cat >&2 <<EOF
ERROR: An admin credential is required to create the bot.

Create a personal access token in Rocket.Chat:
  Click your account profile icon, then Profile > Personal Access Tokens
  (direct URL: https://rocket.codimeo.com/account/tokens)

  Enter a name, choose "Ignore Two Factor Authentication", click "Add",
  verify with your password or 2FA code if prompted, then copy the user ID
  and access token from the success dialog. The token is shown only once.

Then either export:
  RC_ADMIN_USER_ID=...
  RC_ADMIN_TOKEN=...

or write them to $admin_env:
  RC_ADMIN_USER_ID=...
  RC_ADMIN_TOKEN=...

The admin token is used once and is not written to the skill .env.
EOF
  exit 1
fi

admin_curl() {
  curl -sS -m 30 \
    -H "X-User-Id: ${RC_ADMIN_USER_ID}" \
    -H "X-Auth-Token: ${RC_ADMIN_TOKEN}" \
    "$@"
}

printf 'Checking admin credential...\n'
me="$(admin_curl "${RC_URL%/}/api/v1/me")" || {
  printf 'ERROR: Admin request failed.\n' >&2
  exit 1
}
if [[ "$(jq -r '.success // false' <<<"$me")" != "true" ]]; then
  printf 'ERROR: Admin authentication failed. Check RC_ADMIN_USER_ID / RC_ADMIN_TOKEN.\n' >&2
  exit 1
fi
if ! jq -e '.roles | index("admin")' >/dev/null 2>&1 <<<"$me"; then
  printf 'ERROR: The supplied credential does not belong to an admin user.\n' >&2
  exit 1
fi
printf 'Admin OK: %s\n' "$(jq -r '.username' <<<"$me")"

if ! command -v python3 >/dev/null 2>&1; then
  printf 'ERROR: python3 is required for setup.\n' >&2
  exit 1
fi
bot_password="$(python3 -c 'import secrets, string; a=string.ascii_lowercase; A=string.ascii_uppercase; d=string.digits; s="!@#$%^&*"; print("".join([secrets.choice(a), secrets.choice(A), secrets.choice(d), secrets.choice(s)] + [secrets.choice(a+A+d+s) for _ in range(24)]))')"
if [[ -z "$bot_password" ]]; then
  printf 'ERROR: Could not generate a bot password.\n' >&2
  exit 1
fi

printf 'Looking up bot user %s...\n' "$RC_BOT_USERNAME"
existing="$(admin_curl --get --data-urlencode "username=${RC_BOT_USERNAME}" "${RC_URL%/}/api/v1/users.info")"
bot_id=""

if [[ "$(jq -r '.success // false' <<<"$existing")" == "true" ]]; then
  bot_id="$(jq -r '.user._id' <<<"$existing")"
  printf 'Bot exists (%s); resetting password and ensuring admin role...\n' "$bot_id"
  update_body="$(jq -n \
    --arg id "$bot_id" \
    --arg password "$bot_password" \
    '{userId:$id, data:{password:$password, roles:["user","admin"], active:true, requirePasswordChange:false}}')"
  updated="$(admin_curl -X POST -H 'Content-Type: application/json' -d "$update_body" "${RC_URL%/}/api/v1/users.update")"
  if [[ "$(jq -r '.success // false' <<<"$updated")" != "true" ]]; then
    printf 'ERROR: Could not update the bot user.\n' >&2
    jq -r '{status,error,message} | to_entries[] | "  \(.key): \(.value)"' <<<"$updated" >&2 || true
    exit 1
  fi
else
  printf 'Creating bot user...\n'
  create_body="$(jq -n \
    --arg username "$RC_BOT_USERNAME" \
    --arg email "$RC_BOT_EMAIL" \
    --arg name "$RC_BOT_NAME" \
    --arg password "$bot_password" \
    '{username:$username, email:$email, name:$name, password:$password,
      roles:["user","admin"], verified:true, requirePasswordChange:false,
      sendWelcomeEmail:false, joinDefaultChannels:false}')"
  created="$(admin_curl -X POST -H 'Content-Type: application/json' -d "$create_body" "${RC_URL%/}/api/v1/users.create")"
  if [[ "$(jq -r '.success // false' <<<"$created")" != "true" ]]; then
    printf 'ERROR: Could not create the bot user.\n' >&2
    jq -r '{status,error,message} | to_entries[] | "  \(.key): \(.value)"' <<<"$created" >&2 || true
    exit 1
  fi
  bot_id="$(jq -r '.user._id' <<<"$created")"
fi

if [[ -z "$bot_id" ]]; then
  printf 'ERROR: Could not determine the bot user id.\n' >&2
  exit 1
fi

printf 'Logging in as the bot...\n'
login_body="$(jq -n --arg user "$RC_BOT_USERNAME" --arg password "$bot_password" '{user:$user, password:$password}')"
login="$(curl -sS -m 30 -H 'Content-Type: application/json' -d "$login_body" "${RC_URL%/}/api/v1/login")"
bot_auth_token="$(jq -r '.data.authToken // empty' <<<"$login")"
login_user_id="$(jq -r '.data.userId // empty' <<<"$login")"

if [[ -z "$bot_auth_token" ]]; then
  printf 'ERROR: Bot login failed.\n' >&2
  jq -r '{status,error,message} | to_entries[] | "  \(.key): \(.value)"' <<<"$login" >&2 || true
  if [[ "$(jq -r '.error // empty' <<<"$login")" == "totp-required" ]]; then
    cat >&2 <<'EOF'

The workspace auto-enrolls new users in email 2FA, which blocks bot login.
Disable email 2FA for this bot only, then rerun this script.

On the Rocket.Chat host:
  docker exec rocketchat-mongodb-1 mongosh --quiet --eval \
    'db.getSiblingDB("rocketchat").users.updateOne({username:"rocket-admin-bot"},{$set:{"services.email2fa.enabled":false}})'

EOF
  fi
  exit 1
fi
[[ -n "$login_user_id" ]] && bot_id="$login_user_id"

printf 'Generating a personal access token for the bot...\n'
pat_body="$(jq -n '{tokenName:"rocket-admin-skill", bypassTwoFactor:true}')"
pat="$(curl -sS -m 30 \
  -H "X-User-Id: ${bot_id}" \
  -H "X-Auth-Token: ${bot_auth_token}" \
  -H 'Content-Type: application/json' \
  -d "$pat_body" \
  "${RC_URL%/}/api/v1/users.generatePersonalAccessToken")"
bot_pat="$(jq -r '.token // empty' <<<"$pat")"

if [[ -z "$bot_pat" ]]; then
  printf 'ERROR: Could not generate a personal access token for the bot.\n' >&2
  jq -r '{status,error,message} | to_entries[] | "  \(.key): \(.value)"' <<<"$pat" >&2 || true
  exit 1
fi

umask 077
tmp="$(mktemp "${RC_ENV_FILE}.XXXXXX")"
{
  printf '%s\n' '# rocket-admin skill credentials. Generated locally; do not commit or share.'
  printf 'RC_URL=%q\n' "${RC_URL%/}"
  printf 'RC_USER_ID=%q\n' "$bot_id"
  printf 'RC_AUTH_TOKEN=%q\n' "$bot_pat"
  printf 'RC_BOT_USERNAME=%q\n' "$RC_BOT_USERNAME"
} > "$tmp"
chmod 600 "$tmp"
mv "$tmp" "$RC_ENV_FILE"

printf 'Verifying the new bot token...\n'
verify="$(curl -sS -m 30 \
  -H "X-User-Id: ${bot_id}" \
  -H "X-Auth-Token: ${bot_pat}" \
  "${RC_URL%/}/api/v1/me")"
if [[ "$(jq -r '.success // false' <<<"$verify")" == "true" ]]; then
  printf 'OK: bot is ready and .env was written.\n'
  jq -r '"  user: \(.username)  roles: \(.roles | join(","))"' <<<"$verify"
else
  printf 'ERROR: Bot token verification failed.\n' >&2
  exit 1
fi
