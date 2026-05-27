---
name: google-calendar
description: Full read/write access to Google Calendar via OAuth2 API. List events, create/update/delete events, check free/busy, search across all calendars. Supports multiple Google accounts.
---

# Google Calendar Skill

Full access to Google Calendar — read events, create/update/delete, check free/busy, search.

## Project Structure

```
google-calendar/
├── SKILL.md                  # This file
├── credentials.json          # Local OAuth2 client credentials (git-ignored; DO NOT commit)
├── token.json                # Local OAuth token (git-ignored; DO NOT commit)
└── scripts/
    ├── auth.py               # OAuth2 flow + token management
    ├── events.py             # List / search events
    └── manage.py             # Create / update / delete / free-busy
```

---

## Setup (One-Time)

### 1. Google Cloud Console

1. Go to https://console.cloud.google.com
2. Create or select a project (e.g. `pi-agent`)
3. **Enable Google Calendar API**: APIs & Services → Library → "Google Calendar API" → Enable
4. **Create OAuth credentials**: APIs & Services → Credentials → Create Credentials → OAuth client ID
   - Application type: **Desktop app** — Name: `pi-agent`
5. **Download JSON** → save as `~/.agents/skills/google-calendar/credentials.json`
6. **OAuth consent screen**: External → add your email as test user

### 2. Authenticate

```bash
python3 ~/.agents/skills/google-calendar/scripts/auth.py
```

This opens a browser tab, you approve access, token is saved to `token.json`. Done.

### 3. Check auth status

```bash
python3 ~/.agents/skills/google-calendar/scripts/auth.py --check
```

---

## Reading Events

### Today
```bash
python3 scripts/events.py
```

### Next N days
```bash
python3 scripts/events.py --days=7
```

### Specific date
```bash
python3 scripts/events.py --date=2026-05-28
```

### Date range
```bash
python3 scripts/events.py --from=2026-05-27 --to=2026-05-29
```

### Search by keyword
```bash
python3 scripts/events.py --search="standup"
```

### Filter by calendar
```bash
python3 scripts/events.py --calendar="primary" --days=7
```

### List all calendars
```bash
python3 scripts/events.py --calendars
```

### JSON output (for scripting)
```bash
python3 scripts/events.py --date=2026-05-28 --json
```

---

## Creating Events

```bash
# Timed event
python3 scripts/manage.py create \
  --title="Standup" \
  --date=2026-05-28 \
  --start=09:00 --end=09:30 \
  --calendar="primary"

# With location and description
python3 scripts/manage.py create \
  --title="Client meeting" \
  --date=2026-05-28 \
  --start=14:00 --end=15:00 \
  --location="Google Meet" \
  --description="Q2 review" \
  --calendar="primary"

# All-day event
python3 scripts/manage.py create \
  --title="Conference" \
  --date=2026-05-28 \
  --calendar="primary"

# With attendees (sends invites)
python3 scripts/manage.py create \
  --title="Team sync" \
  --date=2026-05-28 \
  --start=10:00 --end=10:30 \
  --attendees="alice@example.com,bob@example.com" \
  --calendar="primary"
```

---

## Updating Events

```bash
python3 scripts/manage.py update \
  --event-id=<event_id> \
  --calendar-id=primary \
  --title="New title" \
  --start=10:30 --end=11:00
```

---

## Deleting Events

```bash
python3 scripts/manage.py delete \
  --event-id=<event_id> \
  --calendar-id=primary
```

---

## Free/Busy Check

```bash
# Is Thursday free?
python3 scripts/manage.py freebusy \
  --from=2026-05-28 \
  --calendar="primary"

# Range
python3 scripts/manage.py freebusy \
  --from=2026-05-28 --to=2026-05-30 \
  --calendar="primary"
```

---

## How It Works

### Authentication
- OAuth2 "Desktop app" flow — no server needed
- First run: opens browser → user approves → saves `token.json`
- Subsequent runs: auto-refreshes token silently
- Scopes: `calendar` (full read/write) + `calendar.events`

### API Endpoints Used
| Operation | API Call |
|---|---|
| List calendars | `calendarList().list()` |
| List events | `events().list(calendarId, timeMin, timeMax)` |
| Search events | `events().list(..., q=query)` |
| Create event | `events().insert(calendarId, body)` |
| Update event | `events().update(calendarId, eventId, body)` |
| Delete event | `events().delete(calendarId, eventId)` |
| Free/busy | `freebusy().query(timeMin, timeMax, items)` |

### Key Files
| File | Description |
|---|---|
| `credentials.json` | Local OAuth2 client ID + secret from Google Cloud Console. Git-ignored; do not commit. |
| `token.json` | Local access + refresh token. Git-ignored; do not commit. |

### Event labels / colors — important limitation

Google Calendar's public API exposes event colors as numeric `colorId` values only. It **does not expose the user's custom label names** (for example: `Formation`, `Client`, `Personal`). The API can read/write `event.colorId`, but cannot list custom label names or map a name to a color directly.

When the user asks to apply a named label/color and the mapping is unknown:

1. **Do not guess** based on existing event colors.
2. Ask the user to manually apply their preferred label/color to one representative event in Google Calendar.
3. Re-fetch that event via `events().list()` or `events().get()` and read its `colorId`.
4. Ask for confirmation before applying that `colorId` to other events.
5. Apply the confirmed `colorId` with `events().patch(calendarId, eventId, body={"colorId": "<id>"})`.

Example workflow:

```text
User: Give these events the label Formation.
Agent: Google Calendar API cannot see label names. Please apply Formation to one of these events manually, then tell me when done.
User: Done, I applied it to the first event.
Agent: Re-fetches the first event, sees colorId=11, confirms, then patches the remaining events with colorId=11.
```

Useful snippet:

```python
# Infer label/color from an example event already labeled by the user
example = service.events().get(calendarId=cal_id, eventId=example_event_id).execute()
color_id = example.get("colorId")

# Apply after user confirmation
service.events().patch(
    calendarId=cal_id,
    eventId=target_event_id,
    body={"colorId": color_id},
).execute()
```

Optional user label mappings can be kept in a local, git-ignored notes file if needed. Do not commit personal calendar labels or event details.

Legacy event color palette exposed by API:

| colorId | Hex |
|---|---|
| `1` | `#a4bdfc` |
| `2` | `#7ae7bf` |
| `3` | `#dbadff` |
| `4` | `#ff887c` |
| `5` | `#fbd75b` |
| `6` | `#ffb878` |
| `7` | `#46d6db` |
| `8` | `#e1e1e1` |
| `9` | `#5484ed` |
| `10` | `#51b749` |
| `11` | `#dc2127` |

---

## Agent Usage Patterns

When the user asks about calendar:

```
"What's on my calendar today?"
→ python3 scripts/events.py

"What do I have this week?"
→ python3 scripts/events.py --days=7

"Am I free Thursday afternoon?"
→ python3 scripts/manage.py freebusy --from=2026-05-28 --calendar="primary"
   + python3 scripts/events.py --date=2026-05-28

"Add a meeting with X on Friday at 2pm"
→ python3 scripts/manage.py create --title="Meeting with X" --date=2026-05-29 --start=14:00 --end=15:00

"Cancel the standup on Monday"
→ First: python3 scripts/events.py --date=2026-06-01 --search="standup" --json  (find event ID)
→ Then:  python3 scripts/manage.py delete --event-id=<id> --calendar-id=<cal>
```

Always confirm with user before creating, updating, or deleting events.

For named labels/colors, never assume the name → `colorId` mapping. Ask the user to label one event manually first, read that event's `colorId`, then apply it to the remaining events only after confirmation. Keep any personal label mappings in local git-ignored notes, not in this public repository.
