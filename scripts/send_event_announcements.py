import sys
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Allow imports from the backend root directory
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from __init__ import app, db

from model.calendar import Event

from model.subscription import (
    Subscription,
    EventNotification,
    EventAnnouncement
)

from services.event_notifications import send_event_email


def send_announcements(dry_run=True):

    today = datetime.now(
        ZoneInfo("America/Los_Angeles")
    ).date().isoformat()

    announcements = EventAnnouncement.query.filter_by(
        processed=False
    ).order_by(
        EventAnnouncement.created_at.asc()
    ).all()

    subscribers = Subscription.query.filter_by(
        confirmed=True,
        active=True,
        event_announcements=True
    ).all()

    sent = 0
    skipped = 0
    failed = 0
    processed = 0
    pending = 0

    print("==============================")
    print("NCSNCF Event Announcement Worker")
    print("==============================")

    print(f"Dry run: {dry_run}")
    print(f"Pending announcements: {len(announcements)}")
    print(f"Eligible subscribers: {len(subscribers)}")

    for announcement in announcements:

        event = db.session.get(
            Event,
            announcement.event_id
        )

        # Ignore deleted or expired events
        if not event or event.date < today:

            print(
                f"Skipping unavailable or expired event "
                f"{announcement.event_id}"
            )

            if not dry_run:
                announcement.processed = True
                announcement.processed_at = datetime.now(
                    timezone.utc
                )
                db.session.commit()
                processed += 1

            continue

        print(f"\nProcessing event: {event.title}")
        print(f"Event date: {event.date}")

        event_failed = False

        for subscriber in subscribers:

            # Refresh subscription status before delivery
            db.session.refresh(subscriber)

            if (
                not subscriber.active
                or not subscriber.confirmed
                or not subscriber.event_announcements
            ):
                skipped += 1
                continue

            existing = EventNotification.query.filter_by(
                subscription_id=subscriber.id,
                event_id=event.id,
                notification_type="announcement"
            ).first()

            if existing:
                skipped += 1
                continue

            if dry_run:
                pending += 1
                continue

            try:

                result = send_event_email(
                    subscriber,
                    event,
                    "announcement"
                )

                if result:
                    sent += 1
                else:
                    skipped += 1

            except Exception:

                db.session.rollback()

                failed += 1
                event_failed = True

                app.logger.error(
                    "Announcement delivery failed for event %s",
                    event.id
                )

        # Mark complete only if delivery did not fail
        if not dry_run and not event_failed:

            announcement.processed = True

            announcement.processed_at = datetime.now(
                timezone.utc
            )

            db.session.commit()

            processed += 1

    print("\n==============================")
    print("Announcement Summary")
    print("==============================")

    print(f"Announcements processed: {processed}")
    print(f"Emails pending in dry run: {pending}")
    print(f"Emails sent: {sent}")
    print(f"Emails skipped: {skipped}")
    print(f"Failed deliveries: {failed}")

    return failed


if __name__ == "__main__":

    with app.app_context():

        failed = send_announcements(
            dry_run="--send" not in sys.argv
        )

    sys.exit(1 if failed else 0)