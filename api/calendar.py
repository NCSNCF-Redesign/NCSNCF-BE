from flask import Blueprint, jsonify
from model.calendar import Event

calendar_api = Blueprint('calendar_api', __name__, url_prefix='/api')

@calendar_api.route('/events', methods=['GET'])
def get_events():
    events = Event.query.all()
    return jsonify([event.read() for event in events])