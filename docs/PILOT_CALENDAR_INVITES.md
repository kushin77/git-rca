# Pilot Calendar Invite Templates

This file contains copy-paste calendar invite templates and guidance for scheduling pilot sessions for the Investigation Canvas.

Usage:
- Copy the preferred template and paste into your calendar application's event body.
- Replace placeholders (in ALL CAPS) with real values: `HOST_NAME`, `ATTENDEE_NAME`, `ATTENDEE_EMAIL`, `TIME_SLOT`, `DURATION`, `TIMEZONE`, `JOIN_LINK`.

---

## 1) Short Invitation (Email + Calendar Body)

Subject: Invitation: Investigation Canvas Pilot Session — [PROPOSED DATE/TIME]

Body:
Hi ATTENDEE_NAME,

You're invited to a short pilot session to review and validate the Investigation Canvas — a lightweight UI and API for root-cause investigations. The session will run for DURATION minutes and include a short walkthrough and feedback collection.

Proposed slot: TIME_SLOT (TIMEZONE)

Agenda:
- 5 min — Quick intro and objective
- 15–20 min — Live demo and walk-through
- 10–15 min — Q&A and feedback

Join: JOIN_LINK

Please reply to the invitation issue with RSVP (Yes / No / Maybe) and preferred alternate times if the proposed slot doesn't work.

Thanks,
HOST_NAME

---

## 2) Calendar Event Description (ICS-friendly / copy-paste into description)

Title: Investigation Canvas — Pilot Session (DURATION minutes)

Location: Virtual — JOIN_LINK

Description:
Investigation Canvas pilot session. Please review the short demo and provide feedback on usability, clarity, and feature fit.

Agenda:
- Intro and goals
- Demo: create investigation, link events, add annotations
- Collect feedback and capture action items

Notes:
- If you cannot attend, reply in the issue with your availability and I'll share a recording.

Contact: HOST_NAME (HOST_EMAIL)

---

## 3) Internal Organizer Template (copy into calendar invite organizer field)

- Event owner: HOST_NAME
- Organizer email: HOST_EMAIL
- Preparation: Confirm screen sharing, demo dataset loaded, test audio
- Follow-up: Capture notes in docs/PILOT_FEEDBACK_SUMMARY.md and open follow-up issues as needed

---

## 4) Batch Send Instructions

If you have the list of attendee emails, use your calendar client to create an event using the above templates and add attendees. When sending by GitHub comment or email, include the time slot and join link and ask attendees to add to their calendar.

For privacy and deliverability:
- Use BCC for large email lists (or an internal inviteer who can schedule via corporate calendar).
- Avoid posting personal emails publicly in issue comments.

---

## 5) Example (filled)

Subject: Invitation: Investigation Canvas Pilot — Wed Jan 28 2026 16:00 UTC

Body:
Hi Team,

You're invited to a 45-minute pilot session for the Investigation Canvas on Wed Jan 28 2026 16:00 UTC (45 minutes).

Join: https://meet.example.com/abc-123

Agenda:
- 5 min — Intro
- 25 min — Demo
- 15 min — Feedback

Please RSVP in the issue or reply to this message with availability.

Thanks,
HOST_NAME
