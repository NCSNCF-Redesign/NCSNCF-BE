from flask import Blueprint, jsonify

# Initialize the Blueprint (this tells Flask this file contains routes)
calendar_api = Blueprint('calendar_api', __name__, url_prefix='/api')

# Define the data abstraction (Python list of dictionaries)
event_list = [
    { "title": "Jazz Night", "date": "October 25 | Concert Hall", "category": "Concerts" },
    { "title": "Blood Memory", "date": "October 26 | Museum", "category": "Exhibits" },
    { "title": "Beginner Swing Classes", "date": "November 7 | Studios", "category": "Workshops" },
    { "title": "Jane Monheit Quartet", "date": "November 19 | Center Theater", "category": "Concerts" }
]

# Create the GET endpoint
@calendar_api.route('/events', methods=['GET'])
def get_events():
    # Return the python list as a JSON response
    return jsonify(event_list)