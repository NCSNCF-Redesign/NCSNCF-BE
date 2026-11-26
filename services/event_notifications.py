import os
import json
from urllib.request import Request, urlopen
from urllib.parse import urlencode

from itsdangerous import URLSafeTimedSerializer
from __init__ import db
from model.subscription import Subscription, EventNotification


def get_serializer():
    secret = os.environ["SUBSCRIPTION_SECRET"]
    return URLSafeTimedSerializer(secret)


def generate_token(subscription, purpose):
    return get_serializer().dumps(
        {
            "id": subscription.id,
            "version": subscription.token_version
        },
        salt=purpose
    )


def read_token(token, purpose, max_age=None):
    return get_serializer().loads(
        token,
        salt=purpose,
        max_age=max_age
    )


def subscription_link(subscription, purpose):
    base_url = os.environ["PUBLIC_API_URL"].rstrip("/")
    token = generate_token(subscription, purpose)

    return (
        f"{base_url}/api/subscriptions/{purpose}?"
        + urlencode({"token": token})
    )


def send_email(recipient, subject, body, idempotency_key=None):
    api_key = os.environ["RESEND_API_KEY"]
    sender = os.environ["SUBSCRIPTION_FROM_EMAIL"]

    payload = {
        "from": sender,
        "to": [recipient],
        "subject": subject,
        "text": body
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key

    request = Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def send_confirmation_email(subscription):
    confirm_url = subscription_link(
        subscription,
        "confirm"
    )

    body = f"""
Thank you for subscribing to NCSNCF!

Confirm your email address to receive upcoming
community events, registration announcements,
and event reminders.

Confirm your subscription:
{confirm_url}

If you did not request this subscription,
you can ignore this email.

North County Special Needs Community Foundation
"""

    return send_email(
        subscription.email,
        "Confirm your NCSNCF subscription",
        body
    )


def send_event_email(subscription, event, notification_type):
    if notification_type not in ("announcement", "reminder"):
        raise ValueError("Invalid notification type")

    if not subscription.confirmed or not subscription.active:
        return False

    if notification_type == "announcement":
        if not subscription.event_announcements:
            return False
        subject = f"New NCSNCF Event: {event.title}"
    else:
        if not subscription.event_reminders:
            return False
        subject = f"Upcoming Event Reminder: {event.title}"

    existing = EventNotification.query.filter_by(
        subscription_id=subscription.id,
        event_id=event.id,
        notification_type=notification_type
    ).first()

    if existing:
        return False

    unsubscribe_url = subscription_link(
        subscription,
        "unsubscribe"
    )

    calendar_url = os.environ["PUBLIC_CALENDAR_URL"]

    body = f"""
North County Special Needs Community Foundation

{subject}

Event: {event.title}
Date: {event.date}
Time: {event.time or "See event calendar"}
Location: {event.location}
Category: {event.category}
Format: {event.format or "See event calendar"}

Registration Information:
{event.cost_rsvp or "See event calendar"}

Event Description:
{event.description or ""}

View our event calendar:
{calendar_url}

You are receiving this email because you subscribed
to NCSNCF community event notifications.

Unsubscribe:
{unsubscribe_url}

{os.environ["SUBSCRIPTION_MAILING_ADDRESS"]}
"""

    send_email(
        subscription.email,
        subject,
        body,
        idempotency_key=(
            f"event-{event.id}-"
            f"subscriber-{subscription.id}-"
            f"{notification_type}"
        )
    )

    notification = EventNotification(
        subscription_id=subscription.id,
        event_id=event.id,
        notification_type=notification_type
    )

    try:
        db.session.add(notification)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return True