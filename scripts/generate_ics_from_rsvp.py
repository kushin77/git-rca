#!/usr/bin/env python3
import re
from pathlib import Path

INPUT = Path("docs/PILOT_RSVP_TEMPLATE.md")
OUTDIR = Path("docs/ICS_INVITES")
OUTDIR.mkdir(parents=True, exist_ok=True)

md = INPUT.read_text()
# find aggregated RSVPs section
m = re.search(r"## Aggregated RSVPs(.*)", md, re.S)
if not m:
    print("No aggregated RSVPs found")
    raise SystemExit(1)
block = m.group(1)
lines = [l.strip() for l in block.splitlines() if l.strip().startswith("|")]
entries = []
for line in lines:
    cols = [c.strip() for c in line.split("|")]
    # expect: | repo | issue URL | respondent | comment |
    if len(cols) >= 5:
        repo = cols[1]
        issue = cols[2]
        respondent = cols[3]
        comment = cols[4]
        if repo and issue and respondent:
            entries.append((repo, issue, respondent, comment))

seen = set()
for repo, issue, respondent, comment in entries:
    key = (repo, issue, respondent)
    if key in seen:
        continue
    seen.add(key)
    safe_repo = repo.replace("/", "_")
    safe_resp = re.sub(r"[^A-Za-z0-9_-]", "_", respondent) if respondent else "unknown"
    fname = OUTDIR / f"{safe_repo}__{safe_resp}.ics"
    # basic ICS template with placeholders
    ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Git RCA//Investigation Canvas Pilot//EN
BEGIN:VEVENT
UID:{safe_repo}-{safe_resp}@git-rca
DTSTAMP:20260127T000000Z
DTSTART:20260203T160000Z
DTEND:20260203T164500Z
SUMMARY:Investigation Canvas Pilot (45 minutes)
DESCRIPTION:Investigation Canvas pilot session. Reply in the issue to confirm attendance.\nIssue: {issue}\nRespondent: {respondent}\nNotes: {comment}
LOCATION:Virtual — https://meet.example.com/INVITE-CODE
ORGANIZER;CN=Git RCA Team:mailto:host@example.com
ATTENDEE;CN={respondent};RSVP=TRUE:mailto:{safe_resp}@example.invalid
END:VEVENT
END:VCALENDAR
"""
    fname.write_text(ics)
    print("Wrote", fname)

print("Created", len(seen), "ICS files in", OUTDIR)
