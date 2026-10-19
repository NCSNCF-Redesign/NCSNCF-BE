# Refactored: Use CRUD naming (read, create) in InfoModel
from flask import Flask, jsonify, request
import os
from flask_cors import CORS
from flask_restful import Api, Resource
from events import get_all_events  # Import your function/data from events.py

app = Flask(__name__)

# Only allow the CCAE frontend (deployed and local dev)
CORS(
    app,
    supports_credentials=True,
    origins=[
        "https://ccae-redesign-team.github.io",  # deployed CCAE-FE
        "http://localhost:4000",                 # local frontend (adjust to port)
        "http://localhost:4500",
    ],
)

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
        return jsonify(info_model.read())

    def post(self):
        # Add a new entry to InfoDb
        entry = request.get_json()
        if not entry:
            return {"error": "No data provided"}, 400
        info_model.create(entry)
        return {"message": "Entry added successfully", "entry": entry}, 201


api.add_resource(DataAPI, "/api/data")


# We can use @app.route for HTML endpoints, this will be style for Admin UI
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)))

@app.route('/api/events', methods=['GET'])
def get_events():
    """Returns the master list of CCAE events."""
    return jsonify(EVENTS_DATABASE), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
