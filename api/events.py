# Data Abstraction: List of event dictionaries stored in backend state
EVENTS_DATABASE = [
    {
        "id": "evt_101",
        "title": "Beginner Pottery Workshop",
        "category": "Arts",
        "price": 45,
        "capacity": 15,
        "date": "2026-10-20"
    },
    {
        "id": "evt_102",
        "title": "Jazz Night & Jam Session",
        "category": "Music",
        "price": 0,
        "capacity": 0,
        "date": "2026-11-05"
    }
]

def get_all_events():
    """Returns the list of events."""
    return EVENTS_DATABASE