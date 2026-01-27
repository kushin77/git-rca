# Pilot Onboarding Guide

This guide walks a pilot user through running their first RCA using the Git RCA Workspace.

1. Setup
   - Clone the repository and create a working branch.
   - (Optional) Create a Python virtualenv: `python -m venv .venv && source .venv/bin/activate`.
   - Install dependencies: `pip install -r requirements.txt`.

2. Run the app locally
   - Start the dev sandbox: `docker-compose -f infra/docker-compose.yml up --build` or `python -m src.app`.
   - Visit http://localhost:8080 and confirm the site loads.

3. Create an investigation
   - Use the API or UI: `POST /api/investigations` with JSON `{ "title": "Pilot RCA" }`.
   - Note the returned investigation ID.

4. Link events and add annotations (manual for pilot)
   - Use the UI to add events or use the API to POST events/annotations once endpoints are available.

5. Export and share findings
   - Use the Export/Share buttons in the UI (mock implementation currently) or copy the investigation JSON.

6. Provide feedback
   - Complete the pilot survey (link provided by maintainers) and add issues for high-priority items.

Notes
- This is a lightweight onboarding guide for pilot users; expand with screenshots and videos as the UI stabilizes.
