import csv
import io
from flask import flash, Response
import hashlib
import secrets
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from flask import (
    Blueprint,
    jsonify,
    request,
    abort,
    render_template,
    redirect,
    url_for,
    session,
    current_app
)
from flask_login import current_user, login_required
from sqlalchemy import func, update
from sqlalchemy.exc import IntegrityError
from __init__ import db
from model.calendar import Event
from model.event_registration import (
    EventRegistration,
    EventRegistrationSettings
)
event_registration_api = Blueprint(
    "event_registration_api",
    __name__,
    url_prefix="/api"
)
def hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
def confirmed_attendees(event_id):
    return db.session.query(
        func.coalesce(
            func.sum(
                EventRegistration.adults +
                EventRegistration.children
            ),
            0
        )
    ).filter(
        EventRegistration.event_id == event_id,
        EventRegistration.status == "confirmed"
    ).scalar()
def registration_open(event, settings):
    if not settings or not settings.enabled:
        return False
    today = datetime.now(
        ZoneInfo("America/Los_Angeles")
    ).date().isoformat()
    if event.date < today:
        return False
    if settings.registration_deadline:
        deadline = settings.registration_deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) >= deadline:
            return False
    return True
def lock_event(event_id):
    # Serialize registration changes for the same event.
    db.session.execute(
        update(Event)
        .where(Event.id == event_id)
        .values(title=Event.title)
    )
def validate_registration(data):
    if not isinstance(data, dict):
        raise ValueError("Invalid registration data.")
    name = data.get("full_name", "")
    email = data.get("email", "")
    notes = data.get("accommodation_notes", "")
    if not all(isinstance(v, str) for v in (name, email, notes)):
        raise ValueError("Invalid text fields.")
    name = name.strip()
    email = email.strip().lower()
    notes = notes.strip()
    if not name or len(name) > 150:
        raise ValueError("Enter a valid full name.")
    if len(email) > 254 or not re.fullmatch(
        r"[^@\s]+@[^@\s]+\.[^@\s]+", email
    ):
        raise ValueError("Enter a valid email address.")
    adults = data.get("adults", 1)
    children = data.get("children", 0)
    if type(adults) is not int or type(children) is not int:
        raise ValueError("Attendee counts must be whole numbers.")
    if adults < 1 or children < 0:
        raise ValueError("At least one adult attendee is required.")
    if adults + children > 20:
        raise ValueError("Maximum 20 attendees per registration.")
    if len(notes) > 1000:
        raise ValueError("Accommodation notes are too long.")
    return name, email, adults, children, notes
# ==========================================================
# PUBLIC EVENT AVAILABILITY
# ==========================================================
@event_registration_api.route(
    "/events/<int:event_id>/availability",
    methods=["GET"]
)
def get_availability(event_id):
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({"error": "Event not found."}), 404
    settings = db.session.get(
        EventRegistrationSettings, event_id
    )
    if not settings or not settings.enabled:
        return jsonify({
            "registration_enabled": False,
            "registration_open": False
        }), 200
    confirmed = confirmed_attendees(event_id)
    remaining = (
        None if settings.capacity is None
        else max(0, settings.capacity - confirmed)
    )
    return jsonify({
        "registration_enabled": True,
        "registration_open": registration_open(event, settings),
        "capacity": settings.capacity,
        "confirmed_attendees": confirmed,
        "spots_remaining": remaining,
        "waitlist_enabled": settings.waitlist_enabled
    }), 200
# ==========================================================
# SUBMIT A NEW RSVP
# ==========================================================
@event_registration_api.route(
    "/events/<int:event_id>/register",
    methods=["POST"]
)
def register_for_event(event_id):
    try:
        name, email, adults, children, notes = (
            validate_registration(request.get_json(silent=True))
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    try:
        lock_event(event_id)
        event = db.session.get(Event, event_id)
        settings = db.session.get(
            EventRegistrationSettings, event_id
        )
        if not event:
            db.session.rollback()
            return jsonify({"error": "Event not found."}), 404
        if not registration_open(event, settings):
            db.session.rollback()
            return jsonify({
                "error": "Registration is closed."
            }), 403
        existing = EventRegistration.query.filter_by(
            event_id=event_id,
            email=email
        ).first()
        if existing:
            db.session.rollback()
            return jsonify({
                "error": (
                    "Unable to create another registration. "
                    "Use your existing registration or contact staff."
                )
            }), 409
        total = adults + children
        if settings.capacity is not None and total > settings.capacity:
            db.session.rollback()
            return jsonify({"error": "Your party exceeds the total event capacity."}), 400
        confirmed = confirmed_attendees(event_id)
        status = "confirmed"
        existing_waitlist = EventRegistration.query.filter_by(
            event_id=event_id,
            status="waitlisted"
        ).first()
        insufficient_capacity = (
            settings.capacity is not None
            and confirmed + total > settings.capacity
        )
        if insufficient_capacity or existing_waitlist:
            if settings.waitlist_enabled:
                status = "waitlisted"
            else:
                db.session.rollback()
                return jsonify({
                    "error": (
                        "This event does not have available "
                        "registration spots."
                    )
                }), 409
        token = secrets.token_urlsafe(32)
        registration = EventRegistration(
            event_id=event_id,
            full_name=name,
            email=email,
            adults=adults,
            children=children,
            accommodation_notes=notes or None,
            status=status,
            token_hash=hash_token(token)
        )
        db.session.add(registration)
        db.session.flush()
        registration_id = registration.id
        db.session.commit()
        response = jsonify({
            "message": (
                "RSVP confirmed."
                if status == "confirmed"
                else "Added to the waitlist."
            ),
            "registration_id": registration_id,
            "event_id": event_id,
            "status": status,
            "total_attendees": total,
            "management_token": token
        })
        response.headers["Cache-Control"] = "no-store"
        return response, 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "error": "Unable to create registration."
        }), 409
    except Exception:
        db.session.rollback()
        raise
# ==========================================================
# REGISTRATION TOKEN AUTHORIZATION
# ==========================================================
def authorized_registration(registration_id):
    token = request.headers.get("X-Registration-Token", "")
    if not token or len(token) > 128:
        return None
    registration = db.session.get(
        EventRegistration, registration_id
    )
    if not registration:
        return None
    if not secrets.compare_digest(
        registration.token_hash,
        hash_token(token)
    ):
        return None
    return registration
# ==========================================================
# AUTOMATIC WAITLIST PROMOTION
# ==========================================================
def promote_waitlist(event_id, settings):
    event = db.session.get(Event, event_id)
    if not event or not registration_open(event, settings):
        return
    confirmed = confirmed_attendees(event_id)
    waitlisted = EventRegistration.query.filter_by(
        event_id=event_id,
        status="waitlisted"
    ).order_by(
        EventRegistration.created_at.asc(),
        EventRegistration.id.asc()
    ).all()
    for registration in waitlisted:
        total = registration.total_attendees
        if (
            settings.capacity is not None
            and confirmed + total > settings.capacity
        ):
            break
        registration.status = "confirmed"
        confirmed += total
    db.session.flush()
# ==========================================================
# CANCEL AN EXISTING RSVP
# ==========================================================
@event_registration_api.route(
    "/registrations/<int:registration_id>",
    methods=["DELETE"]
)
def cancel_registration(registration_id):
    registration = authorized_registration(registration_id)
    if not registration:
        return jsonify({
            "error": "Invalid registration credentials."
        }), 403
    event_id = registration.event_id
    # End the initial read transaction before acquiring the lock.
    db.session.rollback()
    try:
        lock_event(event_id)
        registration = authorized_registration(registration_id)
        if not registration:
            db.session.rollback()
            return jsonify({
                "error": "Invalid registration credentials."
            }), 403
        if registration.status == "cancelled":
            db.session.rollback()
            return jsonify({
                "message": "Registration already cancelled."
            }), 200
        registration.status = "cancelled"
        db.session.flush()
        settings = db.session.get(
            EventRegistrationSettings,
            event_id
        )
        if settings:
            promote_waitlist(event_id, settings)
        db.session.commit()
        return jsonify({
            "message": "Registration cancelled successfully."
        }), 200
    except Exception:
        db.session.rollback()
        raise
# ==========================================================
# ADMIN REGISTRATION DASHBOARD
# ==========================================================
@event_registration_api.route(
    "/events/<int:event_id>/registrations/admin",
    methods=["GET", "POST"]
)
@login_required
def manage_registrations(event_id):
    if not current_user.is_admin():
        abort(403)
    if "rsvp_csrf_token" not in session:
        session["rsvp_csrf_token"] = secrets.token_urlsafe(32)
    error = None
    # Save registration settings
    if request.method == "POST":
        submitted_token = request.form.get("csrf_token", "")
        if not secrets.compare_digest(
            submitted_token.encode("utf-8"),
            session["rsvp_csrf_token"].encode("utf-8")
        ):
            abort(403)
        try:
            capacity_raw = request.form.get(
                "capacity", ""
            ).strip()
            capacity = (
                int(capacity_raw)
                if capacity_raw else None
            )
            if capacity is not None and not 1 <= capacity <= 100000:
                raise ValueError(
                    "Capacity must be between 1 and 100,000."
                )
            deadline_raw = request.form.get(
                "registration_deadline", ""
            ).strip()
            deadline = None
            if deadline_raw:
                deadline = datetime.strptime(
                    deadline_raw,
                    "%Y-%m-%dT%H:%M"
                ).replace(
                    tzinfo=ZoneInfo("America/Los_Angeles")
                ).astimezone(
                    timezone.utc
                ).replace(tzinfo=None)
            # End the authentication read transaction before locking.
            db.session.rollback()
            lock_event(event_id)
            event = db.session.get(Event, event_id)
            if not event:
                abort(404)
            confirmed = confirmed_attendees(event_id)
            if capacity is not None and capacity < confirmed:
                raise ValueError(
                    "Capacity cannot be lower than "
                    "the confirmed attendee count."
                )
            settings = db.session.get(
                EventRegistrationSettings,
                event_id
            )
            if settings is None:
                settings = EventRegistrationSettings(
                    event_id=event_id
                )
                db.session.add(settings)
            settings.enabled = (
                request.form.get("enabled") == "on"
            )
            if capacity is not None and EventRegistration.query.filter(
                EventRegistration.event_id == event_id,
                EventRegistration.status == "waitlisted",
                EventRegistration.adults + EventRegistration.children > capacity
            ).first():
                raise ValueError("Capacity cannot be smaller than an existing waitlisted party.")
            settings.capacity = capacity
            settings.waitlist_enabled = (
                request.form.get("waitlist_enabled") == "on"
            )
            settings.registration_deadline = deadline
            db.session.flush()
            if settings.enabled:
                promote_waitlist(event_id, settings)
            db.session.commit()
            return redirect(
                url_for(
                    "event_registration_api.manage_registrations",
                    event_id=event_id
                )
            )
        except ValueError as exc:
            db.session.rollback()
            error = str(exc)
        except Exception:
            db.session.rollback()
            raise
    # Load event information
    event = db.session.get(Event, event_id)
    if not event:
        abort(404)
    settings = db.session.get(
        EventRegistrationSettings,
        event_id
    )
    # Load registered attendees
    registrations = EventRegistration.query.filter_by(
        event_id=event_id
    ).order_by(
        EventRegistration.created_at.desc()
    ).all()
    # Calculate dashboard statistics
    confirmed = sum(
        registration.total_attendees
        for registration in registrations
        if registration.status == "confirmed"
    )
    waitlisted = sum(
        registration.total_attendees
        for registration in registrations
        if registration.status == "waitlisted"
    )
    cancelled = sum(
        1
        for registration in registrations
        if registration.status == "cancelled"
    )
    deadline_value = ""
    if settings and settings.registration_deadline:
        deadline = settings.registration_deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(
                tzinfo=timezone.utc
            )
        deadline_value = deadline.astimezone(
            ZoneInfo("America/Los_Angeles")
        ).strftime("%Y-%m-%dT%H:%M")
    # Render administrator dashboard
    response = current_app.make_response(
        render_template(
            "event_registrations.html",
            event=event,
            settings=settings,
            registrations=registrations,
            confirmed=confirmed,
            waitlisted=waitlisted,
            cancelled=cancelled,
            deadline_value=deadline_value,
            csrf_token=session["rsvp_csrf_token"],
            error=error
        )
    )
    response.headers["Cache-Control"] = "no-store"
    return response

@event_registration_api.route("/events/<int:event_id>/registrations/admin/<int:registration_id>/cancel", methods=["POST"])
@login_required
def admin_cancel_registration(event_id, registration_id):
    if not current_user.is_admin():
        abort(403)
    expected = session.get("rsvp_csrf_token", "")
    submitted = request.form.get("csrf_token", "")
    if not expected or not secrets.compare_digest(expected.encode(), submitted.encode()):
        abort(403)
    db.session.rollback()
    try:
        lock_event(event_id)
        registration = EventRegistration.query.filter_by(id=registration_id, event_id=event_id).first()
        if registration is None:
            abort(404)
        if registration.status != "cancelled":
            registration.status = "cancelled"
            db.session.flush()
            settings = db.session.get(EventRegistrationSettings, event_id)
            if settings:
                promote_waitlist(event_id, settings)
            db.session.commit()
            flash("Registration cancelled. Eligible waitlisted parties have been promoted if registration is open.", "success")
        else:
            db.session.rollback()
            flash("Registration was already cancelled.", "info")
    except Exception:
        db.session.rollback()
        raise
    return redirect(url_for("event_registration_api.manage_registrations", event_id=event_id))


def csv_safe(value):
    text = str(value or "") if not isinstance(value, int) else str(value)
    if text.lstrip().startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n")):
        return "'" + text
    return text


@event_registration_api.route("/events/<int:event_id>/registrations/admin/export", methods=["GET"])
@login_required
def export_registrations(event_id):
    if not current_user.is_admin():
        abort(403)
    if db.session.get(Event, event_id) is None:
        abort(404)
    status = request.args.get("status", "confirmed")
    if status not in ("all", "confirmed", "waitlisted", "cancelled"):
        abort(400)
    query = EventRegistration.query.filter_by(event_id=event_id)
    if status != "all":
        query = query.filter_by(status=status)
    output = io.StringIO(newline="")
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    writer.writerow(["Name", "Email", "Adults", "Children", "Total", "Status", "Registered (UTC)"])
    for row in query.order_by(EventRegistration.created_at.asc(), EventRegistration.id.asc()).all():
        writer.writerow([csv_safe(v) for v in (row.full_name, row.email, row.adults, row.children, row.total_attendees, row.status, row.created_at.isoformat())])
    return Response(output.getvalue(), content_type="text/csv; charset=utf-8", headers={
        "Content-Disposition": f'attachment; filename="event-{event_id}-{status}.csv"',
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff"
    })


@event_registration_api.app_context_processor
def bulk_rsvp_context():
    if request.endpoint == "manage_events" and current_user.is_authenticated and current_user.is_admin():
        if "rsvp_csrf_token" not in session:
            session["rsvp_csrf_token"] = secrets.token_urlsafe(32)
        return {"bulk_rsvp_csrf_token": session["rsvp_csrf_token"]}
    return {}


@event_registration_api.route("/events/registrations/admin/bulk", methods=["POST"])
@login_required
def bulk_registration_settings():
    if not current_user.is_admin():
        abort(403)
    expected = session.get("rsvp_csrf_token", "")
    submitted = request.form.get("csrf_token", "")
    if not expected or not secrets.compare_digest(expected.encode(), submitted.encode()):
        abort(403)
    action = request.form.get("rsvp_action")
    if action not in ("enable", "disable"):
        abort(400)
    try:
        ids = sorted(set(int(value) for value in request.form.getlist("event_ids")))
    except ValueError:
        abort(400)
    if not ids or any(event_id <= 0 for event_id in ids):
        flash("Select at least one event.", "rsvp_bulk_error")
        return redirect(url_for("manage_events"))
    db.session.rollback()
    changed = 0
    try:
        for event_id in ids:
            lock_event(event_id)
            if db.session.get(Event, event_id) is None:
                db.session.rollback()
                flash("An event no longer exists. No changes were saved.", "rsvp_bulk_error")
                return redirect(url_for("manage_events"))
            settings = db.session.get(EventRegistrationSettings, event_id)
            if settings is None:
                if action == "disable":
                    continue
                settings = EventRegistrationSettings(event_id=event_id, enabled=True, capacity=None, waitlist_enabled=True)
                db.session.add(settings)
                changed += 1
            elif settings.enabled != (action == "enable"):
                settings.enabled = action == "enable"
                changed += 1
            else:
                continue
            db.session.flush()
            if settings.enabled:
                promote_waitlist(event_id, settings)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    flash(f"RSVPs {action}d for {changed} event(s). {len(ids) - changed} already had that setting.", "rsvp_bulk_success")
    return redirect(url_for("manage_events"))
