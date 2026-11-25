# imports from flask
from urllib.parse import urljoin, urlparse
from flask import abort, redirect, render_template, request, send_from_directory, url_for, jsonify, current_app, g # import render_template from "public" flask libraries
from flask_login import current_user, login_user, logout_user
from flask.cli import AppGroup
from flask_login import current_user, login_required
from flask import current_app
from dotenv import load_dotenv

# import "objects" from "this" project
from __init__ import app, db, login_manager  # Key Flask objects 
from model.persona import Persona, initPersonas, initPersonaUsers
from model.presence_schedule import seed_schedules
# API endpoints
from api.user import user_api 
from api.python_exec_api import python_exec_api
from api.javascript_exec_api import javascript_exec_api
from api.section import section_api
from api.persona_api import persona_api
from api.skill_snapshot_api import skill_passport_api
from api.pfp import pfp_api
from api.analytics import analytics_api
from api.student import student_api
from api.groq_api import groq_api
from api.gemini_api import gemini_api
from api.ainpc_api import ainpc_api
from api.microblog_api import microblog_api
from api.classroom_api import classroom_api
from api.data_export_import_api import data_export_import_api
from api.leaderboard import dynamic_api, events_api
from hacks.joke import joke_api  # Import the joke API blueprint
from api.post import post_api  # Import the social media post API
from api.congrats_api import congrats_api  # Import the congrats API
from api.profile_game import profile_game_api  # CS Pathway Game profile persistence
from api.snapshot_proxy import snapshot_proxy
from api.rfid_api import rfid_api
from api.presence_api import presence_api
#from api.announcement import announcement_api ##temporary revert
from api.calendar import calendar_api
from api.resources import resources_api
from api.survey import survey_api # Import your survey blueprint

# database Initialization functions
from model.user import User, initUsers
from model.user import Section;
from model.github import GitHubUser
from model.feedback import Feedback
from api.analytics import get_date_range
# from api.grade_api import grade_api
from api.study import study_api
from api.feedback_api import feedback_api
from model.study import Study, initStudies
from model.classroom import Classroom
from model.skill_snapshot import SkillSnapshot
from model.post import Post, init_posts
from model.microblog import MicroBlog, Topic, initMicroblogs
from model.leaderboard import ScoreCounterEvent, ElementaryLeaderboardEvent
from hacks.jokes import initJokes 
from model.calendar import Event
# from model.announcement import Announcement ##temporary revert

# server only Views

import calendar
import os
from datetime import date, datetime, timedelta

# Load environment variables
load_dotenv()

# register URIs for api endpoints
app.register_blueprint(python_exec_api)
app.register_blueprint(javascript_exec_api)
app.register_blueprint(user_api)
app.register_blueprint(section_api)
app.register_blueprint(persona_api)
app.register_blueprint(skill_passport_api)
app.register_blueprint(pfp_api) 
app.register_blueprint(groq_api)
app.register_blueprint(gemini_api)
app.register_blueprint(ainpc_api)
app.register_blueprint(microblog_api)

app.register_blueprint(analytics_api)
app.register_blueprint(student_api)
# app.register_blueprint(grade_api)
app.register_blueprint(study_api)
app.register_blueprint(classroom_api)
app.register_blueprint(feedback_api)
app.register_blueprint(data_export_import_api)  # Register the data export/import API
app.register_blueprint(dynamic_api)  # Register the dynamic leaderboard API
app.register_blueprint(events_api)  # Register the elementary leaderboard API
app.register_blueprint(survey_api)  # Register the survey API
app.register_blueprint(joke_api)  # Register the joke API blueprint
app.register_blueprint(post_api)  # Register the social media post API
app.register_blueprint(congrats_api)  # Register the congrats message API
app.register_blueprint(profile_game_api)  # CS Pathway Game profile persistence
app.register_blueprint(snapshot_proxy)  # Register the snapshot proxy API
app.register_blueprint(rfid_api)  # Register the RFID attendance API
app.register_blueprint(presence_api)  # Register the generic presence event API
# app.register_blueprint(announcement_api) ##temporary revert
app.register_blueprint(calendar_api)
app.register_blueprint(resources_api)

# Jokes file initialization
with app.app_context():
    db.create_all()
    initJokes()

# Tell Flask-Login the view function name of your login route
login_manager.login_view = "login"

@login_manager.unauthorized_handler
def unauthorized_callback():
    return redirect(url_for('login', next=request.path))

# register URIs for server pages
@login_manager.user_loader
def load_user(user_id):
    # user_id is the composite "id:token_version" from User.get_id(). A mismatched
    # token_version means the session predates a password change on this account --
    # returning None here tells Flask-Login the session is invalid.
    #
    # A session issued before this field existed at all has no ":" -- treat that as
    # token_version "0" (matching a fresh/unchanged account) instead of invalidating
    # it outright. It still correctly fails below once the account's real
    # token_version has moved past 0 from an actual password change.
    if ":" in user_id:
        raw_id, token_version = user_id.split(":", 1)
    else:
        raw_id, token_version = user_id, "0"
    try:
        raw_id = int(raw_id)
    except ValueError:
        return None
    user = User.query.get(raw_id)
    if user is None or str(user.token_version) != token_version:
        return None
    return user

@app.context_processor
def inject_user():
    return dict(current_user=current_user)

# Helper function to check if the URL is safe for redirects
def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    next_page = request.args.get('next', '') or request.form.get('next', '')
    if request.method == 'POST':
        user = User.query.filter_by(_uid=request.form['username']).first()
        if user and user.is_password(request.form['password']) and not user.active:
            error = 'Account pending verification.'
        elif user and user.is_password(request.form['password']):
            login_user(user)
            if not is_safe_url(next_page):
                return abort(400)
            return redirect(next_page or url_for('index'))
        else:
            error = 'Invalid username or password.'
    return render_template("login.html", error=error, next=next_page)

@app.route('/studytracker')  # route for the study tracker page
def studytracker():
    return render_template("studytracker.html")

@app.route('/congrats')
@login_required
def congrats():
    from model.congrats_message import CongratsMessage

    messages = CongratsMessage.get_by_user(current_user.id)
    return render_template("congrats.html", messages=messages, project="Congrats Messages")

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.errorhandler(404)  # catch for URL not found
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template('404.html'), 404

@app.route('/')  # connects default URL to index() function
def index():
    print("Home:", current_user)
    return render_template("index.html")



@app.route('/users/table2')
@login_required
def u2table():
    users = User.query.all()
    return render_template("u2table.html", user_data=users, role_options=current_user.grantable_roles())

@app.route('/sections/')
@login_required
def sections():
    sections = Section.query.all()
    return render_template("sections.html", sections=sections)

@app.route('/persona/')
@login_required
def persona():
    personas = Persona.query.all()
    return render_template("persona.html", personas=personas)

# Helper function to extract uploads for a user (ie PFP image)
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
 
@app.route('/users/delete/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    user = User.query.get(user_id)
    if user:
        blocker = user.deletion_blocker(current_user)
        if blocker:
            return jsonify({'error': blocker[1]}), blocker[0]
        user.delete()
        return jsonify({'message': 'User deleted successfully'}), 200
    return jsonify({'error': 'User not found'}), 404

@app.route('/users/reset_password/<int:user_id>', methods=['POST'])
@login_required
def reset_password(user_id):
    if not current_user.is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Set the new password
    if user.update({"password": app.config['DEFAULT_PASSWORD']}):
        return jsonify({'message': 'Password reset successfully'}), 200
    return jsonify({'error': 'Password reset failed'}), 500

@app.route('/update_user/<string:uid>', methods=['PUT'])
def update_user(uid):
    # Authorization check
    if not current_user.is_admin():
        return jsonify({'error': 'Unauthorized'}), 403

    # Get the JSON data from the request
    data = request.get_json()
    print(f"Request Data: {data}")  # Log the incoming data

    # Find the user in the database
    user = User.query.filter_by(_uid=uid).first()
    if user:
        print(f"Found user: {user.uid}")  # Log the found user's UID
        
        # Update the user using the provided data
        user.update(data)  # Assuming `user.update(data)` is a method on your User model
        
        # Save changes to the database
        return jsonify({"message": "User updated successfully."}), 200
    else:
        print("User not found.")  # Log when user is not found
        return jsonify({"message": "User not found."}), 404

@app.route('/survey_results')
@login_required
def survey_results():
    return render_template("survey_results.html")

def generate_event_dates(start_str, repeat="none", until_str=None, max_events=52):
    start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
    if repeat == "none":
        return [start_date]

    if not until_str:
        raise ValueError("Please select a Repeat Until date for recurring events.")

    end_date = datetime.strptime(until_str, "%Y-%m-%d").date()
    if end_date < start_date:
        raise ValueError("Repeat Until date must be on or after the event start date.")

    dates = []
    current = start_date
    step = 1

    while current <= end_date and len(dates) < max_events:
        dates.append(current)
        if repeat == "daily":
            current += timedelta(days=1)
        elif repeat == "weekly":
            current += timedelta(weeks=1)
        elif repeat == "biweekly":
            current += timedelta(weeks=2)
        elif repeat == "monthly":
            month = start_date.month - 1 + step
            year = start_date.year + month // 12
            month = month % 12 + 1
            day = min(start_date.day, calendar.monthrange(year, month)[1])
            current = start_date.replace(year=year, month=month, day=day)
            step += 1
        else:
            break

    return dates

def format_optional_time(raw_time):
    cleaned = (raw_time or "").strip()
    if not cleaned:
        return None
    try:
        return datetime.strptime(cleaned, "%H:%M").strftime("%I:%M %p").lstrip("0")
    except ValueError:
        return cleaned

@app.route('/events', methods=['GET', 'POST'])
@login_required
def manage_events():
    if not current_user.is_admin():
        return abort(403)

    min_date = (date.today() + timedelta(days=1)).isoformat()
    error = None

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        event_date = request.form.get('date', '').strip()
        raw_end_date = request.form.get('end_date', '').strip()
        raw_time = request.form.get('time', '').strip()
        raw_end_time = request.form.get('end_time', '').strip()
        location = request.form.get('location', '').strip()
        category = request.form.get('category', '').strip()
        event_format = request.form.get('format', 'In-person').strip()
        cost_rsvp = request.form.get('cost_rsvp', '').strip()
        description = request.form.get('description', '').strip()
        repeat = request.form.get('repeat', 'none').strip()
        repeat_until = request.form.get('repeat_until', '').strip()

        if not event_date or event_date < min_date:
            error = "Event date must be in the future."
        elif raw_end_date and raw_end_date < event_date:
            error = "End date must be on or after the event start date."
        else:
            try:
                formatted_time = format_optional_time(raw_time)
                formatted_end_time = format_optional_time(raw_end_time)
                event_dates = generate_event_dates(event_date, repeat, repeat_until)

                duration = None
                if raw_end_date:
                    start_dt = datetime.strptime(event_date, "%Y-%m-%d").date()
                    end_dt = datetime.strptime(raw_end_date, "%Y-%m-%d").date()
                    duration = end_dt - start_dt

                for occurrence_date in event_dates:
                    occ_end_date = (
                        (occurrence_date + duration).strftime("%Y-%m-%d")
                        if duration is not None else None
                    )
                    new_event = Event(
                        title=title,
                        date=occurrence_date.strftime("%Y-%m-%d"),
                        end_date=occ_end_date,
                        time=formatted_time,
                        end_time=formatted_end_time,
                        location=location,
                        category=category,
                        format=event_format,
                        cost_rsvp=cost_rsvp,
                        description=description
                    )
                    db.session.add(new_event)

                db.session.commit()
                return redirect(url_for('manage_events'))
            except ValueError as e:
                db.session.rollback()
                error = str(e)

    events = Event.query.order_by(Event.date.asc(), Event.time.asc()).all()
    return render_template("events.html", events=events, min_date=min_date, error=error)

@app.route('/events/edit/<int:event_id>', methods=['POST'])
@login_required
def edit_event(event_id):
    if not current_user.is_admin():
        return abort(403)

    event = Event.query.get_or_404(event_id)
    min_date = (date.today() + timedelta(days=1)).isoformat()
    event_date = request.form.get('date', '').strip()
    raw_end_date = request.form.get('end_date', '').strip()
    raw_time = request.form.get('time', '').strip()
    raw_end_time = request.form.get('end_time', '').strip()

    effective_start_date = event_date or event.date

    if event_date and event_date < min_date:
        events = Event.query.order_by(Event.date.asc(), Event.time.asc()).all()
        return render_template(
            "events.html",
            events=events,
            min_date=min_date,
            error="Event date must be in the future."
        )

    if raw_end_date and raw_end_date < effective_start_date:
        events = Event.query.order_by(Event.date.asc(), Event.time.asc()).all()
        return render_template(
            "events.html",
            events=events,
            min_date=min_date,
            error="End date must be on or after the event start date."
        )

    if event_date:
        event.date = event_date

    event.end_date = raw_end_date or None
    event.time = format_optional_time(raw_time)
    event.end_time = format_optional_time(raw_end_time)

    event.title = request.form.get('title', event.title)
    event.location = request.form.get('location', event.location)
    event.category = request.form.get('category', event.category)
    event.format = request.form.get('format', event.format)
    event.cost_rsvp = request.form.get('cost_rsvp', '').strip()
    event.description = request.form.get('description', '')

    db.session.commit()
    return redirect(url_for('manage_events'))

@app.route('/events/delete/<int:event_id>', methods=['POST'])
@login_required
def delete_event(event_id):
    if not current_user.is_admin():
        return abort(403)

    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    return redirect(url_for('manage_events'))

# Create an AppGroup for custom commands
custom_cli = AppGroup('custom', help='Custom commands')

# Database Model for Storing Editable Page Content
class PageContent(db.Model):
    __tablename__ = 'page_content'
    id = db.Column(db.Integer, primary_key=True)
    page_key = db.Column(db.String(50), unique=True, nullable=False) # e.g., 'home'
    hero_title = db.Column(db.String(200), nullable=True)
    org_subtitle = db.Column(db.String(200), nullable=True)
    hero_desc = db.Column(db.Text, nullable=True)

    def read(self):
        return {
            "page_key": self.page_key,
            "hero_title": self.hero_title,
            "org_subtitle": self.org_subtitle,
            "hero_desc": self.hero_desc
        }


class Milestone(db.Model):
    __tablename__ = 'milestones'
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    display_order = db.Column(db.Integer, default=0)

    def read(self):
        return {
            "id": self.id,
            "year": self.year,
            "title": self.title,
            "description": self.description,
            "image_url": self.image_url,
            "display_order": self.display_order
        }

# Get all milestones
@app.route('/api/milestones', methods=['GET'])
def get_milestones():
    milestones = Milestone.query.order_by(Milestone.display_order.asc(), Milestone.id.asc()).all()
    return jsonify([m.read() for m in milestones]), 200

# Create a new milestone
@app.route('/api/milestones', methods=['POST'])
def create_milestone():
    data = request.get_json() or {}
    img_url = data.get('image_url', '').strip()
    if not img_url:
        img_url = None

    milestone = Milestone(
        year=data.get('year', ''),
        title=data.get('title', ''),
        description=data.get('description', ''),
        image_url=img_url,
        display_order=data.get('display_order', 0)
    )
    db.session.add(milestone)
    db.session.commit()
    return jsonify({"message": "Milestone created successfully", "data": milestone.read()}), 201

# Update an existing milestone
@app.route('/api/milestones/<int:milestone_id>', methods=['PUT'])
def update_milestone(milestone_id):
    milestone = Milestone.query.get_or_404(milestone_id)
    data = request.get_json() or {}
    
    milestone.year = data.get('year', milestone.year)
    milestone.title = data.get('title', milestone.title)
    milestone.description = data.get('description', milestone.description)
    
    if 'image_url' in data:
        img_url = data.get('image_url', '').strip()
        milestone.image_url = img_url if img_url else None

    milestone.display_order = data.get('display_order', milestone.display_order)
    
    db.session.commit()
    return jsonify({"message": "Milestone updated successfully", "data": milestone.read()}), 200

# Delete a milestone
@app.route('/api/milestones/<int:milestone_id>', methods=['DELETE'])
def delete_milestone(milestone_id):
    milestone = Milestone.query.get_or_404(milestone_id)
    db.session.delete(milestone)
    db.session.commit()
    return jsonify({"message": "Milestone deleted successfully"}), 200

# API Endpoint to Fetch Home Page Content
@app.route('/api/page-content/<page_key>', methods=['GET'])
def get_page_content(page_key):
    content = PageContent.query.filter_by(page_key=page_key).first()
    if not content:
        # Default fallback content if none saved yet
        return jsonify({
            "hero_title": "Bringing People Together",
            "org_subtitle": "North County Special Needs Community Foundation",
            "hero_desc": "Empowering adults with developmental disabilities in Poway and surrounding communities through heartfelt human connection, social inclusion, lifelong education, and independent housing opportunities."
        }), 200
    return jsonify(content.read()), 200

# API Endpoint to Save/Update Home Page Content
@app.route('/api/page-content/<page_key>', methods=['POST', 'PUT'])
def save_page_content(page_key):
    data = request.get_json() or {}
    content = PageContent.query.filter_by(page_key=page_key).first()
    
    if not content:
        content = PageContent(page_key=page_key)
        db.session.add(content)
        
    if "hero_title" in data:
        content.hero_title = data["hero_title"]
    if "org_subtitle" in data:
        content.org_subtitle = data["org_subtitle"]
    if "hero_desc" in data:
        content.hero_desc = data["hero_desc"]
        
    db.session.commit()
    return jsonify({"message": "Content saved successfully", "data": content.read()}), 200

# Define a command to run the data generation functions
@custom_cli.command('generate_data')
def generate_data():
    initUsers()
    initMicroblogs()
    initPersonas()
    initPersonaUsers()
    seed_schedules()  # presence schedules from model/presence_schedules.json

# Register the custom command group with the Flask application
app.cli.add_command(custom_cli)
        
# this runs the flask application on the development server
if __name__ == "__main__":
    host = "0.0.0.0"
    port = app.config['FLASK_PORT']
    print(f"** Server running: http://localhost:{port}")  # Pretty link
    app.run(debug=True, host=host, port=port, use_reloader=False)