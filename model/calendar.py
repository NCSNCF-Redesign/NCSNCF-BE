from __init__ import db

class Event(db.Model):
    __tablename__ = 'events'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    time = db.Column(db.String(50), nullable=True)
    location = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)

    def __init__(self, title, date, time="", location="", category="", description=""):
        self.title = title
        self.date = date
        self.time = time
        self.location = location
        self.category = category
        self.description = description

    def read(self):
        return {
            "id": self.id,
            "title": self.title,
            "date": self.date,
            "time": self.time,
            "location": self.location,
            "category": self.category,
            "description": self.description
        }