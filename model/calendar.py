from __init__ import db

class Event(db.Model):
    __tablename__ = 'events'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    time = db.Column(db.String(50), nullable=True)
    location = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    format = db.Column(db.String(100), nullable=True, default="In-person")
    cost_rsvp = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)

    def __init__(self, title, date, time="", location="", category="", format="In-person", cost_rsvp="", description=""):
        self.title = title
        self.date = date
        self.time = time
        self.location = location
        self.category = category
        self.format = format
        self.cost_rsvp = cost_rsvp
        self.description = description

    def read(self):
        return {
            "id": self.id,
            "title": self.title,
            "date": self.date,
            "time": self.time,
            "location": self.location,
            "category": self.category,
            "format": self.format,
            "cost_rsvp": self.cost_rsvp,
            "description": self.description
        }