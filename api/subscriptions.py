import re
from datetime import datetime, timezone

from flask import (
    Blueprint,
    request,
    jsonify,
    current_app,
    render_template_string
)

from itsdangerous import BadSignature, SignatureExpired
from sqlalchemy.exc import IntegrityError

from __init__ import db
from model.subscription import Subscription

from services.event_notifications import (
    send_confirmation_email,
    read_token
)


subscriptions_api = Blueprint(
    "subscriptions_api",
    __name__,
    url_prefix="/api/subscriptions"
)


EMAIL_PATTERN = re.compile(
    r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
)


def get_subscription(token, purpose, max_age=None):
    if not token:
        return None

    try:
        data = read_token(
            token,
            purpose,
            max_age=max_age
        )

        subscription = db.session.get(
            Subscription,
            data["id"]
        )

        if not subscription:
            return None

        if subscription.token_version != data["version"]:
            return None

        return subscription

    except (
        BadSignature,
        SignatureExpired,
        KeyError,
        TypeError,
        ValueError
    ):
        return None


def message_page(title, message, token=None, action=None):
    return render_template_string(
        """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport"
                  content="width=device-width, initial-scale=1">
            <meta name="referrer" content="no-referrer">

            <title>{{ title }} | NCSNCF</title>

            <style>
                body {
                    font-family: system-ui, sans-serif;
                    background: #f4f8fa;
                    color: #173b64;
                    margin: 0;
                    padding: 24px;
                }

                main {
                    max-width: 600px;
                    margin: 60px auto;
                    padding: 32px;
                    background: white;
                    border: 1px solid #d3dfe8;
                    border-radius: 12px;
                    text-align: center;
                }

                button {
                    background: #247e83;
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    border-radius: 8px;
                    font: inherit;
                    cursor: pointer;
                }

                a {
                    color: #247e83;
                }
            </style>
        </head>

        <body>
            <main>
                <h1>{{ title }}</h1>
                <p>{{ message }}</p>

                {% if token and action %}
                    <form method="POST">
                        <input type="hidden"
                               name="token"
                               value="{{ token }}">

                        <button type="submit">
                            {{ action }}
                        </button>
                    </form>
                {% endif %}

                <p>
                    <a href="https://ncsncf-redesign.github.io/NCSNCF-FE/">
                        Return to NCSNCF
                    </a>
                </p>
            </main>
        </body>
        </html>
        """,
        title=title,
        message=message,
        token=token,
        action=action
    )


@subscriptions_api.route("", methods=["POST"])
def subscribe():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Invalid request."
        }), 400

    raw_email = data.get("email")

    if not isinstance(raw_email, str):
        return jsonify({
            "error": "Email address is required."
        }), 400

    email = raw_email.strip().lower()

    if len(email) > 254 or not EMAIL_PATTERN.fullmatch(email):
        return jsonify({
            "error": "Enter a valid email address."
        }), 400

    success_message = {
        "message": (
            "If confirmation is needed, "
            "check your email."
        )
    }

    subscription = Subscription.query.filter_by(
        email=email
    ).first()

    if subscription and subscription.confirmed and subscription.active:
        return jsonify(success_message), 200

    if not subscription:
        subscription = Subscription(email=email)

        try:
            db.session.add(subscription)
            db.session.commit()

        except IntegrityError:
            db.session.rollback()

            subscription = Subscription.query.filter_by(
                email=email
            ).first()

            if not subscription:
                return jsonify({
                    "error": "Unable to subscribe."
                }), 503

            if subscription.confirmed and subscription.active:
                return jsonify(success_message), 200

    try:
        send_confirmation_email(subscription)

    except Exception:
        current_app.logger.error(
            "Subscription confirmation delivery failed."
        )

        return jsonify({
            "error": "Email delivery is temporarily unavailable."
        }), 503

    return jsonify(success_message), 200


@subscriptions_api.route(
    "/confirm",
    methods=["GET", "POST"]
)
def confirm():

    token = (
        request.args.get("token")
        if request.method == "GET"
        else request.form.get("token")
    )

    subscription = get_subscription(
        token,
        "confirm",
        max_age=86400
    )

    if not subscription:
        return message_page(
            "Invalid Confirmation Link",
            "This link is invalid or expired. Please subscribe again."
        ), 400

    if request.method == "GET":
        return message_page(
            "Confirm Your Subscription",
            "Confirm that you want to receive NCSNCF event emails.",
            token=token,
            action="Confirm Subscription"
        )

    subscription.confirm()
    db.session.commit()

    return message_page(
        "Subscription Confirmed!",
        "You will now receive upcoming event announcements and reminders."
    )


@subscriptions_api.route(
    "/unsubscribe",
    methods=["GET", "POST"]
)
def unsubscribe():

    token = (
        request.args.get("token")
        if request.method == "GET"
        else request.form.get("token")
    )

    subscription = get_subscription(
        token,
        "unsubscribe"
    )

    if not subscription:
        return message_page(
            "Invalid Unsubscribe Link",
            "This unsubscribe link is invalid or no longer active."
        ), 400

    if request.method == "GET":
        return message_page(
            "Unsubscribe",
            "Would you like to stop receiving NCSNCF event emails?",
            token=token,
            action="Unsubscribe"
        )

    subscription.unsubscribe()
    db.session.commit()

    return message_page(
        "Successfully Unsubscribed",
        "You will no longer receive NCSNCF event emails."
    )