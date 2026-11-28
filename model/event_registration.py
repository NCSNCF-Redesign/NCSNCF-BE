from datetime import datetime, timezone
from __init__ import db


class EventRegistrationSettings(db.Model):
    __tablename__ = "event_registration_settings"

    event_id = db.Column(
        db.Integer,
        db.ForeignKey("events.id", ondelete="CASCADE"),
        primary_key=True
    )

    enabled = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    capacity = db.Column(
        db.Integer,
        nullable=True
    )

    registration_deadline = db.Column(
        db.DateTime,
        nullable=True
    )

    waitlist_enabled = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    event = db.relationship(
        "Event",
        backref=db.backref(
            "registration_settings",
            uselist=False,
            cascade="all, delete-orphan"
        )
    )


class EventRegistration(db.Model):
    __tablename__ = "event_registrations"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    event_id = db.Column(
        db.Integer,
        db.ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    full_name = db.Column(
        db.String(150),
        nullable=False
    )

    email = db.Column(
        db.String(254),
        nullable=False
    )

    adults = db.Column(
        db.Integer,
        nullable=False,
        default=1
    )

    children = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    accommodation_notes = db.Column(
        db.Text,
        nullable=True
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="confirmed"
    )

    token_hash = db.Column(
        db.String(64),
        unique=True,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    event = db.relationship(
        "Event",
        backref=db.backref(
            "registrations",
            cascade="all, delete-orphan"
        )
    )

    __table_args__ = (
        db.UniqueConstraint(
            "event_id",
            "email",
            name="uq_event_registration_email"
        ),
        db.CheckConstraint(
            "adults >= 0 AND children >= 0",
            name="ck_registration_counts"
        ),
        db.CheckConstraint(
            "adults + children > 0",
            name="ck_registration_attendees"
        ),
        db.CheckConstraint(
            "status IN ('confirmed', 'waitlisted', 'cancelled')",
            name="ck_registration_status"
        ),
    )

    @property
    def total_attendees(self):
        return self.adults + self.children

    def read(self):
        return {
            "id": self.id,
            "event_id": self.event_id,
            "full_name": self.full_name,
            "email": self.email,
            "adults": self.adults,
            "children": self.children,
            "total_attendees": self.total_attendees,
            "accommodation_notes": self.accommodation_notes,
            "status": self.status,
            "created_at": self.created_at.isoformat()
        }