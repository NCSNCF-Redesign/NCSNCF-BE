import json
import os
import requests 

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
JSON_FILE_PATH = os.path.join(BASE_DIR, 'instance', 'data', 'events.json')

def load_events():
    """
    Data Abstraction: Loads raw JSON file into an in-memory list of event dictionaries.
    """
    try:
        with open(JSON_FILE_PATH, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_events(events_list):
    """Saves updated event list back to events.json."""
    with open(JSON_FILE_PATH, 'w') as file:
        json.dump(events_list, file, indent=2)

def filter_events_by_criteria(event_list, category_param, min_capacity_param):
    """
    CPT Procedural Abstraction & Algorithm Requirement
    - Parameter 1: category_param (string)
    - Parameter 2: min_capacity_param (int)
    
    Contains:
    - Sequencing: Sequential filter setup and list building.
    - Iteration: 'for' loop traversing event_list.
    - Selection: 'if' conditions checking category and capacity.
    """
    filtered_results = []  # Sequencing step 1

    # Iteration: Loop through every item in the list
    for event in event_list:
        # Selection: Evaluate category match and available spots
        matches_category = (category_param == "All" or event["category"].lower() == category_param.lower())
        has_capacity = event["capacity"] >= min_capacity_param

        if matches_category and has_capacity:
            filtered_results.append(event)  # Sequencing step 2

    return filtered_results