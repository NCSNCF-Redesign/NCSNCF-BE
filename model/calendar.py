from __init__ import db

class Event(db.Model):
    __tablename__ = 'events'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    end_date = db.Column(db.String(50), nullable=True)
    time = db.Column(db.String(50), nullable=True)
    end_time = db.Column(db.String(50), nullable=True)
    location = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    format = db.Column(db.String(100), nullable=True, default="In-person")
    cost_rsvp = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)

    # Thumbnail support (linked to Media Library or direct URL)
    media_id = db.Column(db.Integer, db.ForeignKey('media.id'), nullable=True)
    media = db.relationship('Media', backref=db.backref('events', lazy=True))
    image_url = db.Column(db.String(512), nullable=True)

    def __init__(
        self,
        title,
        date,
        time="",
        location="",
        category="",
        format="In-person",
        cost_rsvp="",
        description="",
        end_date=None,
        end_time=None,
        media_id=None,
        image_url=None
    ):
        self.title = title
        self.date = date
        self.end_date = (end_date or "").strip() or None
        self.time = (time or "").strip() or None
        self.end_time = (end_time or "").strip() or None
        self.location = location
        self.category = category
        self.format = format
        self.cost_rsvp = cost_rsvp
        self.description = description
        self.media_id = media_id or None
        self.image_url = (image_url or "").strip() or None

    def get_thumbnail_url(self):
        # Always use the latest Media URL if linked, otherwise fall back to image_url
        if self.media and self.media.url:
            return self.media.url
        return self.image_url

    def read(self):
        return {
            "id": self.id,
            "title": self.title,
            "date": self.date,
            "end_date": self.end_date,
            "time": self.time,
            "end_time": self.end_time,
            "location": self.location,
            "category": self.category,
            "format": self.format,
            "cost_rsvp": self.cost_rsvp,
            "description": self.description,
            "media_id": self.media_id,
            "image_url": self.get_thumbnail_url(),
            "image_alt": self.media.alt_text if (self.media and self.media.alt_text) else self.title
        }