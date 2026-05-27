#!/usr/bin/env python3
"""
Google Calendar — List & query events.

Usage:
  python3 events.py                          # Today's events
  python3 events.py --days=7                 # Next 7 days
  python3 events.py --date=2026-05-28        # Specific date
  python3 events.py --from=2026-05-27 --to=2026-05-29
  python3 events.py --search="standup"       # Search by keyword
  python3 events.py --calendar="Work"        # Filter by calendar
  python3 events.py --calendars             # List all calendars
  python3 events.py --json                  # Raw JSON output
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone, date
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from auth import get_service

LOCAL_TZ_OFFSET = None  # auto-detect


def local_now():
    return datetime.now().astimezone()


def to_rfc3339(dt):
    return dt.isoformat()


def parse_date_arg(s):
    """Parse YYYY-MM-DD into a timezone-aware datetime (start of day)."""
    d = datetime.strptime(s, "%Y-%m-%d").replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return d.astimezone()


def fmt_event(evt, show_calendar=True):
    """Format a single event for pretty display."""
    summary   = evt.get("summary", "(no title)")
    cal_name  = evt.get("_calendar_name", "")
    location  = evt.get("location", "")
    desc      = evt.get("description", "")
    html_link = evt.get("htmlLink", "")

    start = evt.get("start", {})
    end   = evt.get("end", {})

    # All-day vs timed
    if "date" in start:
        start_str = f"All day  ({start['date']})"
        end_str   = ""
    else:
        s = datetime.fromisoformat(start["dateTime"]).astimezone()
        e = datetime.fromisoformat(end["dateTime"]).astimezone()
        start_str = s.strftime("%H:%M")
        end_str   = e.strftime("%H:%M")

    lines = []
    time_part = f"{start_str}–{end_str}" if end_str else start_str
    cal_part  = f"  [{cal_name}]" if show_calendar and cal_name else ""
    lines.append(f"  🕐 {time_part}{cal_part}  {summary}")
    if location:
        lines.append(f"     📍 {location}")
    if desc:
        short_desc = desc.strip().replace("\n", " ")[:120]
        lines.append(f"     📝 {short_desc}{'…' if len(desc) > 120 else ''}")
    return "\n".join(lines)


def list_calendars(service):
    """Return list of all calendars."""
    result = service.calendarList().list().execute()
    return result.get("items", [])


def fetch_events(service, time_min, time_max, query=None, calendar_ids=None, max_results=250):
    """Fetch events across specified calendars (or all if None)."""
    if calendar_ids is None:
        cals = list_calendars(service)
        calendar_ids = [(c["id"], c.get("summary", c["id"])) for c in cals]
    
    all_events = []
    for cal_id, cal_name in calendar_ids:
        kwargs = dict(
            calendarId=cal_id,
            timeMin=to_rfc3339(time_min),
            timeMax=to_rfc3339(time_max),
            singleEvents=True,
            orderBy="startTime",
            maxResults=max_results,
        )
        if query:
            kwargs["q"] = query
        try:
            result = service.events().list(**kwargs).execute()
            for evt in result.get("items", []):
                evt["_calendar_name"] = cal_name
                all_events.append(evt)
        except Exception:
            pass  # skip calendars we can't read

    # Sort by start time
    def sort_key(e):
        s = e.get("start", {})
        return s.get("dateTime", s.get("date", ""))

    all_events.sort(key=sort_key)
    return all_events


def group_by_date(events):
    """Group events by date."""
    groups = {}
    for evt in events:
        s = evt.get("start", {})
        if "dateTime" in s:
            d = datetime.fromisoformat(s["dateTime"]).astimezone().date()
        else:
            d = date.fromisoformat(s["date"])
        groups.setdefault(d, []).append(evt)
    return groups


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days",      type=int,   default=1)
    parser.add_argument("--date",      type=str,   default=None)
    parser.add_argument("--from",      dest="from_", type=str, default=None)
    parser.add_argument("--to",        type=str,   default=None)
    parser.add_argument("--search",    type=str,   default=None)
    parser.add_argument("--calendar",  type=str,   default=None)
    parser.add_argument("--calendars", action="store_true")
    parser.add_argument("--json",      action="store_true")
    args = parser.parse_args()

    service = get_service()

    # ── List calendars ────────────────────────────────────────
    if args.calendars:
        cals = list_calendars(service)
        if args.json:
            print(json.dumps(cals, indent=2))
        else:
            print(f"\n📅 Google Calendars ({len(cals)})\n")
            for c in cals:
                primary = " ★" if c.get("primary") else ""
                access  = c.get("accessRole", "?")
                print(f"  {c.get('summary', c['id'])}{primary}  [{access}]  — {c['id']}")
            print()
        return

    # ── Time range ────────────────────────────────────────────
    now = local_now()
    if args.date:
        time_min = parse_date_arg(args.date)
        time_max = time_min + timedelta(days=1)
    elif args.from_:
        time_min = parse_date_arg(args.from_)
        time_max = parse_date_arg(args.to) + timedelta(days=1) if args.to else time_min + timedelta(days=1)
    else:
        time_min = now.replace(hour=0, minute=0, second=0, microsecond=0)
        time_max = time_min + timedelta(days=args.days)

    # ── Calendar filter ───────────────────────────────────────
    calendar_ids = None
    if args.calendar:
        cals = list_calendars(service)
        matched = [(c["id"], c.get("summary", c["id"])) for c in cals
                   if args.calendar.lower() in c.get("summary", "").lower()]
        if not matched:
            print(f"❌ No calendar matching '{args.calendar}'", file=sys.stderr)
            sys.exit(1)
        calendar_ids = matched

    # ── Fetch ─────────────────────────────────────────────────
    events = fetch_events(service, time_min, time_max,
                          query=args.search,
                          calendar_ids=calendar_ids)

    if args.json:
        print(json.dumps(events, indent=2, default=str))
        return

    # ── Pretty output ─────────────────────────────────────────
    range_str = time_min.strftime("%a %d %b") 
    if (time_max - time_min).days > 1:
        range_str += " → " + (time_max - timedelta(days=1)).strftime("%a %d %b %Y")
    else:
        range_str += " " + time_min.strftime("%Y")

    print(f"\n📅 Calendar — {range_str}  ({len(events)} event{'s' if len(events) != 1 else ''})\n")

    if not events:
        print("  (nothing scheduled)")
        print()
        return

    groups = group_by_date(events)
    for day, day_events in sorted(groups.items()):
        print(f"  ── {day.strftime('%A %d %B %Y')} ──────────────────────────")
        for evt in day_events:
            print(fmt_event(evt))
        print()


if __name__ == "__main__":
    main()
