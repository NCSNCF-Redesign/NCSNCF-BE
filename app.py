# Refactored: Use CRUD naming (read, create) in InfoModel
from flask import Flask, request
import os
from flask_cors import CORS
from flask_restful import Api, Resource
from api.events import load_events, filter_events_by_criteria  

app = Flask(__name__)

# Allow cross-origin requests for local testing and deployed frontend
CORS(app, supports_credentials=True)

api = Api(app)


# --- Model class for InfoDb with CRUD naming ---
class InfoModel:
    def __init__(self):
        self.data = [
            {
                "FirstName": "Barbara",
                "LastName": "Zhao",
                "DOB": "Unknown",
                "Residence": "San Diego",
                "Email": "N/A",
                "Owns_Cars": "None",
            },
            {
                "FirstName": "Shane",
                "LastName": "Lopez",
                "DOB": "February 27",
                "Residence": "San Diego",
                "Email": "slopez@powayusd.com",
                "Owns_Cars": ["2021-Insight"],
            },
        ]

    def read(self):
        return self.data

    def create(self, entry):
        self.data.append(entry)


# Instantiate the model
info_model = InfoModel()


# --- API Resource ---
class DataAPI(Resource):
    def get(self):
        return info_model.read(), 200

    def post(self):
        # Add a new entry to InfoDb
        entry = request.get_json()
        if not entry:
            return {"error": "No data provided"}, 400
        info_model.create(entry)
        return {"message": "Entry added successfully", "entry": entry}, 201


api.add_resource(DataAPI, "/api/data")


@app.route("/")
def say_hello():
    html_content = """
    <html>
    <head>
        <title>Hello</title>
    </head>
    <body>
        <h2>Hello, World!</h2>
    </body>
    </html>
    """
    return html_content

@app.route('/api/events', methods=['GET'])
def get_events():
    events = load_events()
    # Return Python list directly (Flask handles conversion without jsonify conflict)
    return events, 200

@app.route('/api/events/filter', methods=['GET'])
def get_filtered_events():
    category_query = request.args.get('category', 'All')
    min_capacity_query = int(request.args.get('min_capacity', 0))

    master_event_list = load_events()
    matching_events = filter_events_by_criteria(master_event_list, category_query, min_capacity_query)

    return {
        "status": "success",
        "total_matches": len(matching_events),
        "data": matching_events
    }, 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)