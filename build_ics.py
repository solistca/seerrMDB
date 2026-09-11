#!/usr/bin/env python3
"""Step 2 of the reusable two-step process: JSON fixture list -> .ics file.

Sport-agnostic. Reads the Step-1 JSON schema (team/matches/undetermined) and
produces an Apple Calendar compatible .ics with:
  - DTSTART/DTEND in America/Los_Angeles via a proper embedded VTIMEZONE
    (correct US DST rules), computed from the UK-local kickoff via zoneinfo
    so BST/GMT vs PDT/PST are both handled correctly, no hand-computed offset.
  - TBD-time matches emitted as all-day VALUE=DATE events.
  - No VALARM blocks.
"""
import json
import sys
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

UK_TZ = ZoneInfo("Europe/London")
LA_TZ = ZoneInfo("America/Los_Angeles")
MATCH_DURATION = timedelta(hours=2)  # 90 min + HT + stoppage, generic default

VTIMEZONE_LA = """BEGIN:VTIMEZONE
TZID:America/Los_Angeles
X-LIC-LOCATION:America/Los_Angeles
BEGIN:DAYLIGHT
TZOFFSETFROM:-0800
TZOFFSETTO:-0700
TZNAME:PDT
DTSTART:19700308T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:-0700
TZOFFSETTO:-0800
TZNAME:PST
DTSTART:19701101T020000
RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU
END:STANDARD
END:VTIMEZONE
"""


def fold(line):
    """RFC5545 line folding at 75 octets, continuation lines start with a space."""
    if len(line.encode("utf-8")) <= 75:
        return line
    out = []
    cur = ""
    for ch in line:
        cand = cur + ch
        if len(cand.encode("utf-8")) > 75:
            out.append(cur)
            cur = " " + ch
        else:
            cur = cand
    out.append(cur)
    return "\r\n".join(out)


def esc(text):
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def build_event(match, team, uid_ns):
    opponent = match["opponent"]
    comp = match["competition"]
    home = match["home_or_away"] == "home"
    if home:
        title = f"{team} vs {opponent}"
    else:
        title = f"{opponent} vs {team}"

    desc_lines = [f"Competition: {comp}"]
    if match.get("venue"):
        desc_lines.append(f"Venue: {match['venue']}")
    desc_lines.append(f"Sources checked: {', '.join(match.get('sources_checked', []))}")
    if match.get("note"):
        desc_lines.append(f"Note: {match['note']}")
    description = "\n".join(desc_lines)

    uid = f"{uid_ns}-{match['date']}-{opponent.lower().replace(' ', '-')}@personal-calendar"
    dtstamp = datetime.now(ZoneInfo("UTC")).strftime("%Y%m%dT%H%M%SZ")

    lines = ["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{dtstamp}"]

    is_tbd = match["start_time_local"] == "TBD"
    if is_tbd:
        d = datetime.strptime(match["date"], "%Y-%m-%d").date()
        nxt = d + timedelta(days=1)
        lines.append(f"DTSTART;VALUE=DATE:{d.strftime('%Y%m%d')}")
        lines.append(f"DTEND;VALUE=DATE:{nxt.strftime('%Y%m%d')}")
        title = f"{title} (kickoff TBD)"
    else:
        naive = datetime.strptime(
            f"{match['date']} {match['start_time_local']}", "%Y-%m-%d %H:%M"
        )
        uk_dt = naive.replace(tzinfo=UK_TZ)
        la_start = uk_dt.astimezone(LA_TZ)
        la_end = (uk_dt + MATCH_DURATION).astimezone(LA_TZ)
        lines.append(f"DTSTART;TZID=America/Los_Angeles:{la_start.strftime('%Y%m%dT%H%M%S')}")
        lines.append(f"DTEND;TZID=America/Los_Angeles:{la_end.strftime('%Y%m%dT%H%M%S')}")

    lines.append(f"SUMMARY:{esc(title)} ({esc(comp)})")
    if match.get("venue"):
        lines.append(f"LOCATION:{esc(match['venue'])}")
    lines.append(f"DESCRIPTION:{esc(description)}")
    lines.append("END:VEVENT")
    return [fold(l) for l in lines]


def build_calendar(data):
    team = data["team"]
    uid_ns = team.lower().replace(" ", "-")
    cal_name = f"{team} {data.get('season', '')} Fixtures".strip()

    out = []
    out.append("BEGIN:VCALENDAR")
    out.append("VERSION:2.0")
    out.append(fold(f"PRODID:-//Personal Sports Calendar Generator//{esc(team)}//EN"))
    out.append("CALSCALE:GREGORIAN")
    out.append(fold(f"X-WR-CALNAME:{esc(cal_name)}"))
    out.extend(VTIMEZONE_LA.strip("\n").replace("\n", "\r\n").split("\r\n"))

    for match in data["matches"]:
        out.extend(build_event(match, team, uid_ns))

    out.append("END:VCALENDAR")
    return "\r\n".join(out) + "\r\n"


def main():
    src = sys.argv[1]
    dst = sys.argv[2]
    with open(src) as f:
        data = json.load(f)
    ics = build_calendar(data)
    with open(dst, "w", newline="") as f:
        f.write(ics)
    n_events = ics.count("BEGIN:VEVENT")
    n_tbd = sum(1 for m in data["matches"] if m["start_time_local"] == "TBD")
    print(f"Wrote {dst}: {n_events} events ({n_tbd} TBD all-day)")
    assert ics.count("BEGIN:VEVENT") == ics.count("END:VEVENT")
    assert ics.count("VALARM") == 0
    assert "BEGIN:VTIMEZONE" in ics and "END:VTIMEZONE" in ics
    print("Validation OK: balanced VEVENTs, no VALARM, VTIMEZONE present.")


if __name__ == "__main__":
    main()
