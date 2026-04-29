"""
Weekly agenda — runs every Sunday at 8 pm ET via GitHub Actions.
Pulls the coming week's calendar events + recent email threads, asks Claude
to write a week-preview email, then sends it to EMAIL_RECIPIENT.
"""

import base64
import datetime
import email.mime.text
import os

import anthropic
import pytz
from googleapiclient.errors import HttpError

from config import (
    CLAUDE_MODEL,
    EMAIL_RECIPIENT,
    GMAIL_MAX_THREADS,
    LOCAL_TZ,
    SYSTEM_PROMPT,
    WEEKLY_LOOKAHEAD_DAYS,
)
from google_auth import get_calendar_service, get_gmail_service


# ---------------------------------------------------------------------------
# Calendar helpers
# ---------------------------------------------------------------------------

def fetch_week_events(service) -> list[dict]:
    tz = pytz.timezone(LOCAL_TZ)
    now = datetime.datetime.now(tz)
    # Start from tomorrow (Monday) through end of the lookahead window
    start = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + datetime.timedelta(days=WEEKLY_LOOKAHEAD_DAYS)

    result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=start.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return result.get("items", [])


def format_events_by_day(events: list[dict]) -> str:
    if not events:
        return "No events on the calendar this week."

    tz = pytz.timezone(LOCAL_TZ)
    by_day: dict[str, list[str]] = {}

    for e in events:
        start = e.get("start", {})
        if "dateTime" in start:
            dt = datetime.datetime.fromisoformat(start["dateTime"]).astimezone(tz)
            day_key = dt.strftime("%A, %b %-d")
            time_str = dt.strftime("%-I:%M %p")
        else:
            # All-day event
            dt = datetime.date.fromisoformat(start["date"])
            day_key = dt.strftime("%A, %b %-d")
            time_str = "All day"

        summary = e.get("summary", "(no title)")
        location = e.get("location", "")
        line = f"  - {time_str}: {summary}"
        if location:
            line += f" @ {location}"

        by_day.setdefault(day_key, []).append(line)

    sections = []
    for day, items in by_day.items():
        sections.append(f"**{day}**\n" + "\n".join(items))

    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Gmail helpers (shared logic, slightly different prompt framing)
# ---------------------------------------------------------------------------

def fetch_recent_threads(service) -> list[dict]:
    result = (
        service.users()
        .threads()
        .list(userId="me", maxResults=GMAIL_MAX_THREADS, labelIds=["INBOX"])
        .execute()
    )
    threads = result.get("threads", [])
    detailed = []
    for t in threads:
        thread = (
            service.users()
            .threads()
            .get(userId="me", id=t["id"], format="metadata",
                 metadataHeaders=["Subject", "From", "Date"])
            .execute()
        )
        detailed.append(thread)
    return detailed


def format_threads(threads: list[dict]) -> str:
    if not threads:
        return "No recent email threads."

    lines = []
    for t in threads:
        messages = t.get("messages", [])
        if not messages:
            continue
        headers = {h["name"]: h["value"] for h in messages[0].get("payload", {}).get("headers", [])}
        subject = headers.get("Subject", "(no subject)")
        sender = headers.get("From", "unknown")
        msg_count = len(messages)
        lines.append(f"- [{msg_count} msg{'s' if msg_count != 1 else ''}] {subject} — from {sender}")

    return "\n".join(lines) if lines else "No recent email threads."


# ---------------------------------------------------------------------------
# Claude
# ---------------------------------------------------------------------------

def generate_weekly_agenda(events_text: str, threads_text: str, week_label: str) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], timeout=60.0)

    user_message = f"""\
It is Sunday evening. The upcoming week is {week_label}.

=== CALENDAR — COMING WEEK ===
{events_text}

=== RECENT EMAIL THREADS (things that may carry into the week) ===
{threads_text}

Please write my weekly preview email. Structure:
1. One-sentence week overview.
2. Day-by-day highlights (skip empty days).
3. Email / open-loop items to address this week.
4. A short "This week's priorities" section (3 bullets max).
"""

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


# ---------------------------------------------------------------------------
# Gmail send
# ---------------------------------------------------------------------------

def send_email(service, subject: str, body: str) -> None:
    msg = email.mime.text.MIMEText(body, "plain")
    msg["To"] = EMAIL_RECIPIENT
    msg["From"] = "me"
    msg["Subject"] = subject

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    tz = pytz.timezone(LOCAL_TZ)
    now = datetime.datetime.now(tz)
    monday = now + datetime.timedelta(days=1)
    sunday = monday + datetime.timedelta(days=6)
    week_label = f"{monday.strftime('%b %-d')} – {sunday.strftime('%b %-d, %Y')}"

    cal_service = get_calendar_service()
    gmail_service = get_gmail_service()

    events = fetch_week_events(cal_service)
    threads = fetch_recent_threads(gmail_service)

    events_text = format_events_by_day(events)
    threads_text = format_threads(threads)

    body = generate_weekly_agenda(events_text, threads_text, week_label)

    subject = f"Weekly Agenda — {week_label}"
    send_email(gmail_service, subject, body)
    print(f"Sent: {subject}")


if __name__ == "__main__":
    main()
