#!/bin/bash
# Email Manager Skill — Setup Script
# Run once: chmod +x setup.sh && ./setup.sh

set -e

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_FILE="$SKILL_DIR/scripts/config.json"
FETCH_SCRIPT="$SKILL_DIR/scripts/fetch_emails.py"

echo "📧 Email Manager — Setup"
echo "========================"
echo ""

# 1. Validate Python
if ! command -v python3 &>/dev/null; then
    echo "❌ Python 3 is required. Install it first."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# 2. Make scripts executable
chmod +x "$SKILL_DIR/scripts/"*.py "$SKILL_DIR/scripts/"*.sh 2>/dev/null || true
echo "✅ Scripts made executable"

# 3. Check that config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Config file missing: $CONFIG_FILE"
    exit 1
fi

# 4. Prompt for email configuration
echo ""
echo "📝 Email Configuration"
echo "----------------------"
echo "You need: an IMAP-enabled email account."
echo "For Gmail: Enable IMAP, then create an App Password at:"
echo "  https://myaccount.google.com/apppasswords"
echo ""
echo "For Outlook/Hotmail: Use your regular password or an app password."
echo ""

read -p "IMAP server [imap.gmail.com]: " IMAP_SERVER
IMAP_SERVER=${IMAP_SERVER:-imap.gmail.com}

read -p "IMAP port [993]: " IMAP_PORT
IMAP_PORT=${IMAP_PORT:-993}

read -p "Email address: " EMAIL_USER
read -sp "Password / App Password: " EMAIL_PASS
echo ""

read -p "Use SSL? [yes]: " USE_SSL
USE_SSL=${USE_SSL:-yes}

echo ""
read -p "Invoice storage directory [~/Nextcloud/.../400-Comptabilite/Invoices]: " INVOICE_DIR
INVOICE_DIR=${INVOICE_DIR:-~/Nextcloud/Invoices}

# 5. Update config file using Python for JSON safety
python3 -c "
import json
with open('$CONFIG_FILE') as f:
    cfg = json.load(f)
cfg['imap']['server'] = '$IMAP_SERVER'
cfg['imap']['port'] = $IMAP_PORT
cfg['imap']['username'] = '$EMAIL_USER'
cfg['imap']['password'] = '$EMAIL_PASS'
cfg['imap']['use_ssl'] = '${USE_SSL,,}' == 'yes'
cfg['invoices']['storage_dir'] = '$INVOICE_DIR'
with open('$CONFIG_FILE', 'w') as f:
    json.dump(cfg, f, indent=2)
"

echo ""
echo "✅ Configuration saved to: $CONFIG_FILE"

# 6. Create invoice directory if needed
mkdir -p "$INVOICE_DIR"
echo "✅ Invoice directory ready: $INVOICE_DIR"

# 7. Test IMAP connection
echo ""
echo "🔍 Testing IMAP connection..."
python3 -c "
import json, imaplib
with open('$CONFIG_FILE') as f:
    cfg = json.load(f)
ic = cfg['imap']
try:
    if ic['use_ssl']:
        mail = imaplib.IMAP4_SSL(ic['server'], ic['port'])
    else:
        mail = imaplib.IMAP4(ic['server'], ic['port'])
    mail.login(ic['username'], ic['password'])
    status, folders = mail.list()
    mail.logout()
    print('✅ IMAP connection successful!')
except Exception as e:
    print(f'❌ IMAP connection failed: {e}')
"

echo ""
echo "🚀 Setup complete!"
echo ""
echo "To use, ask pi:"
echo "  \"Check my emails\"                    → Fetch & categorize"
echo "  \"Daily review\"                       → Summary of today"
echo "  \"Extract invoices\"                   → Find invoice emails"
echo "  \"What's urgent in my inbox?\"         → Flag urgent items"
echo ""
