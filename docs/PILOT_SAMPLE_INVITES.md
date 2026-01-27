# Pilot Sample Invites & ICS Template

This file contains a reviewed sample email/calendar invite and a simple ICS template you can use to create calendar events for confirmed participants.

## Sample Email / Calendar Body (for review)

Subject: Invitation: Investigation Canvas Pilot — Tue Feb 3 2026 16:00 UTC

Body:
Hi NAME,

You are invited to participate in a 45-minute pilot session to evaluate the Investigation Canvas (root-cause investigation UI + API). The session will include a short walkthrough and structured feedback.

Date & Time: Tue Feb 3 2026 — 16:00 UTC
Duration: 45 minutes
Join link: https://meet.example.com/INVITE-CODE

Agenda:
- 5 min — Intro & objectives
- 25 min — Live demo and hands-on walkthrough
- 15 min — Feedback & next steps

Please RSVP in the invitation issue or reply with 'Yes', 'No', or 'Maybe' and any preferred alternative times.

Thanks,
HOST_NAME — Git RCA Team

---

## ICS Template (replace placeholders)

BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Git RCA//Pilot Invite//EN
BEGIN:VEVENT
UID:REPLACE-WITH-UNIQUE-ID@example.com
DTSTAMP:20260127T000000Z
DTSTART:20260203T160000Z
DTEND:20260203T164500Z
SUMMARY:Investigation Canvas — Pilot Session
DESCRIPTION:Investigation Canvas pilot session. Join: https://meet.example.com/INVITE-CODE\n\nAgenda:\n- Intro\n- Demo\n- Feedback
LOCATION:Virtual — https://meet.example.com/INVITE-CODE
ORGANIZER;CN=HOST_NAME:mailto:HOST_EMAIL
END:VEVENT
END:VCALENDAR

Save the text above as `invite.ics` and attach when sending calendar invites via email, or import into most calendar clients.

---

## How I can help next
- I can generate per-attendee ICS files and a CSV mapping for bulk uploads if you provide attendee names and emails.
- I can produce multiple time-slot options and draft messages for each slot.
- I will not send invites without explicit permission or attendee emails.
