import sys
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Allow imports from the backend root directory
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from __init__ import app, db
from model.calendar import Event
from model.subscription import Subscription
from services.event_notifications import send_event_email


def send_reminders(dry_run=True):

    timezone = ZoneInfo("America/Los_Angeles")

    tomorrow = (
        datetime.now(timezone).date()
        + timedelta(days=1)
    ).isoformat()

    events = Event.query.filter_by(
        date=tomorrow
    ).all()

    subscribers = Subscription.query.filter_by(
        confirmed=True,
        active=True,
        event_reminders=True
    ).all()

    sent = 0
    skipped = 0
    failed = 0

    print(f"Checking events for {tomorrow}")
    print(f"Upcoming events: {len(events)}")
    print(f"Eligible subscribers: {len(subscribers)}")

    for event in events:
        for subscriber in subscribers:

            if dry_run:
                print(f"Would process reminder for event {event.id}")
                continue

            try:
                result = send_event_email(
                    subscriber,
                    event,
                    "reminder"
                )

                if result:
                    sent += 1
                else:
                    skipped += 1

            except Exception:
                db.session.rollback()
                failed += 1

                app.logger.error(
                    "Reminder failed for event %s",
                    event.id
                )

    print("------------------------")
    print(f"Reminders sent: {sent}")
    print(f"Reminders skipped: {skipped}")
    print(f"Failed reminders: {failed}")

    return failed


if __name__ == "__main__":
    with app.app_context():
        failed = send_reminders(
            dry_run="--send" not in sys.argv
        )

    sys.exit(1 if failed else 0)