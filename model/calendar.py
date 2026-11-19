from __init__ import db

class Event(db.Model):
    __tablename__ = 'events'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)

    def __init__(self, title, date, location="", category="", description=""):
        self.title = title
        self.date = date
        self.location = location
        self.category = category
        self.description = description

    def read(self):
        return {
            "id": self.id,
            "title": self.title,
            "date": self.date,
            "location": self.location,
            "category": self.category,
            "description": self.description
        }