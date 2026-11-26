from datetime import datetime, timezone
from __init__ import db


class Subscription(db.Model):
    __tablename__ = "subscriptions"

    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(
        db.String(254),
        unique=True,
        nullable=False,
        index=True
    )

    confirmed = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    active = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    event_announcements = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    event_reminders = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    token_version = db.Column(
        db.Integer,
        default=1,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    confirmed_at = db.Column(
        db.DateTime,
        nullable=True
    )

    unsubscribed_at = db.Column(
        db.DateTime,
        nullable=True
    )

    def __init__(self, email):
        self.email = email.strip().lower()

    def confirm(self):
        self.confirmed = True
        self.active = True
        self.confirmed_at = datetime.now(timezone.utc)
        self.unsubscribed_at = None

    def unsubscribe(self):
        self.active = False
        self.confirmed = False
        self.token_version += 1
        self.unsubscribed_at = datetime.now(timezone.utc)


class EventNotification(db.Model):
    __tablename__ = "event_notifications"

    id = db.Column(db.Integer, primary_key=True)

    subscription_id = db.Column(
        db.Integer,
        db.ForeignKey("subscriptions.id"),
        nullable=False
    )

    event_id = db.Column(
        db.Integer,
        nullable=False,
        index=True
    )

    notification_type = db.Column(
        db.String(30),
        nullable=False
    )

    sent_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    __table_args__ = (
        db.UniqueConstraint(
            "subscription_id",
            "event_id",
            "notification_type",
            name="unique_event_notification"
        ),
    )


class EventAnnouncement(db.Model):
    __tablename__ = "event_announcements"

    id = db.Column(db.Integer, primary_key=True)

    event_id = db.Column(
        db.Integer,
        nullable=False,
        unique=True,
        index=True
    )

    processed = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    processed_at = db.Column(
        db.DateTime,
        nullable=True
    )