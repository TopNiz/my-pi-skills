#!/usr/bin/env python3
"""
Google Calendar — Create, update, delete events.

Usage:
  # Create
  python3 manage.py create \
    --title="Standup" \
    --date=2026-05-28 \
    --start=09:00 --end=09:30 \
    --calendar="primary" \
    --location="Google Meet" \
    --description="Daily sync"

  # Quick (natural-language style, single string)
  python3 manage.py quick --text="Standup tomorrow 9am 30min"

  # Update
  python3 manage.py update --event-id=<id> --calendar-id=<id> --title="New title" --start=10:00

  # Delete
  python3 manage.py delete --event-id=<id> --calendar-id=<id>

  # Free/busy
  python3 manage.py freebusy --from=2026-05-28 --to=2026-05-29 --calendar="primary"
"""

import json
import os
import sys
from datetime import datetime, timedelta
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from auth import get_service
from events import list_calendars, parse_date_arg


def find_calendar_id(service, name_or_id):
    """Resolve a calendar name or ID to its ID."""
    if "@" in name_or_id or name_or_id == "primary":
        return name_or_id
    cals = list_calendars(service)
    for c in cals:
        if name_or_id.lower() in c.get("summary", "").lower():
            return c["id"]
    return name_or_id  # assume it's already an ID


def create_event(service, args):
    cal_id = find_calendar_id(service, args.calendar or "primary")

    # Detect IANA timezone
    try:
        from zoneinfo import ZoneInfo
        import subprocess
        tz = subprocess.run(["readlink", "/etc/localtime"], capture_output=True, text=True).stdout.strip()
        tz = tz.replace("/var/db/timezone/zoneinfo/", "") if tz else "Europe/Paris"
        ZoneInfo(tz)  # validate
    except Exception:
        tz = "Europe/Paris"

    # Build start/end
    if args.start and ":" in args.start:
        start_dt = datetime.strptime(f"{args.date} {args.start}", "%Y-%m-%d %H:%M")
        end_str   = args.end or (start_dt + timedelta(hours=1)).strftime("%H:%M")
        end_dt    = datetime.strptime(f"{args.date} {end_str}", "%Y-%m-%d %H:%M")
        start_body = {"dateTime": start_dt.isoformat(), "timeZone": tz}
        end_body   = {"dateTime": end_dt.isoformat(),   "timeZone": tz}
    else:
        # All-day
        start_body = {"date": args.date}
        end_body   = {"date": args.date}

    body = {
        "summary":     args.title,
        "start":       start_body,
        "end":         end_body,
    }
    if args.location:    body["location"]    = args.location
    if args.description: body["description"] = args.description
    if args.attendees:
        body["attendees"] = [{"email": e.strip()} for e in args.attendees.split(",")]

    evt = service.events().insert(calendarId=cal_id, body=body,
                                  sendNotifications=bool(args.attendees)).execute()
    print(f"✅ Event created: {evt.get('summary')}")
    print(f"   ID:   {evt['id']}")
    print(f"   Link: {evt.get('htmlLink')}")
    return evt


def update_event(service, args):
    cal_id   = args.calendar_id or "primary"
    evt      = service.events().get(calendarId=cal_id, eventId=args.event_id).execute()

    try:
        from zoneinfo import ZoneInfo
        import subprocess
        tz = subprocess.run(["readlink", "/etc/localtime"], capture_output=True, text=True).stdout.strip()
        tz = tz.replace("/var/db/timezone/zoneinfo/", "") if tz else "Europe/Paris"
        ZoneInfo(tz)
    except Exception:
        tz = "Europe/Paris"

    if args.title:       evt["summary"]     = args.title
    if args.location:    evt["location"]    = args.location
    if args.description: evt["description"] = args.description
    if args.start:
        date_part = evt["start"].get("dateTime", evt["start"].get("date", ""))[:10]
        start_dt  = datetime.strptime(f"{date_part} {args.start}", "%Y-%m-%d %H:%M")
        evt["start"] = {"dateTime": start_dt.isoformat(), "timeZone": tz}
    if args.end:
        date_part = evt["end"].get("dateTime", evt["end"].get("date", ""))[:10]
        end_dt    = datetime.strptime(f"{date_part} {args.end}", "%Y-%m-%d %H:%M")
        evt["end"] = {"dateTime": end_dt.isoformat(), "timeZone": tz}

    updated = service.events().update(calendarId=cal_id, eventId=args.event_id, body=evt).execute()
    print(f"✅ Event updated: {updated.get('summary')}")
    print(f"   Link: {updated.get('htmlLink')}")
    return updated


def delete_event(service, args):
    cal_id = args.calendar_id or "primary"
    service.events().delete(calendarId=cal_id, eventId=args.event_id).execute()
    print(f"✅ Event {args.event_id} deleted from calendar {cal_id}")


def freebusy(service, args):
    from_dt = parse_date_arg(args.from_)
    to_dt   = parse_date_arg(args.to) + timedelta(days=1) if args.to else from_dt + timedelta(days=1)
    cal_id  = find_calendar_id(service, args.calendar or "primary")

    body = {
        "timeMin": from_dt.isoformat(),
        "timeMax": to_dt.isoformat(),
        "items":   [{"id": cal_id}],
    }
    result = service.freebusy().query(body=body).execute()
    busy   = result.get("calendars", {}).get(cal_id, {}).get("busy", [])

    print(f"\n📅 Free/Busy: {from_dt.strftime('%a %d %b')} → {to_dt.strftime('%a %d %b')}\n")
    if not busy:
        print("  ✅ Completely free!")
    else:
        print(f"  ⛔ {len(busy)} busy slot(s):")
        for slot in busy:
            s = datetime.fromisoformat(slot["start"]).astimezone()
            e = datetime.fromisoformat(slot["end"]).astimezone()
            print(f"    {s.strftime('%a %d %b %H:%M')} → {e.strftime('%H:%M')}")
    print()


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")

    # create
    c = sub.add_parser("create")
    c.add_argument("--title",       required=True)
    c.add_argument("--date",        required=True)
    c.add_argument("--start")
    c.add_argument("--end")
    c.add_argument("--calendar",    default="primary")
    c.add_argument("--location")
    c.add_argument("--description")
    c.add_argument("--attendees",   help="Comma-separated emails")

    # update
    u = sub.add_parser("update")
    u.add_argument("--event-id",    dest="event_id",    required=True)
    u.add_argument("--calendar-id", dest="calendar_id", default="primary")
    u.add_argument("--title")
    u.add_argument("--start")
    u.add_argument("--end")
    u.add_argument("--location")
    u.add_argument("--description")

    # delete
    d = sub.add_parser("delete")
    d.add_argument("--event-id",    dest="event_id",    required=True)
    d.add_argument("--calendar-id", dest="calendar_id", default="primary")

    # freebusy
    fb = sub.add_parser("freebusy")
    fb.add_argument("--from", dest="from_", required=True)
    fb.add_argument("--to")
    fb.add_argument("--calendar", default="primary")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    service = get_service()
    dispatch = {
        "create":   create_event,
        "update":   update_event,
        "delete":   delete_event,
        "freebusy": freebusy,
    }
    dispatch[args.command](service, args)


if __name__ == "__main__":
    main()
