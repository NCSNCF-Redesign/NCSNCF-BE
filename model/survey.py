from datetime import datetime
from __init__ import db

class CCAESurvey(db.Model):
    __tablename__ = 'ccae_surveys'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Links to User model
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    organization = db.Column(db.String(255), nullable=False)
    discovery_source = db.Column(db.String(255), nullable=True)
    visit_frequency = db.Column(db.String(255), nullable=True)
    event_types_interested = db.Column(db.JSON, nullable=True)       # Stores list of strings
    attends_with = db.Column(db.String(255), nullable=True)
    main_reason = db.Column(db.String(255), nullable=True)
    travel_distance = db.Column(db.String(255), nullable=True)
    discovery_channels = db.Column(db.JSON, nullable=True)           # Stores list of strings
    decision_factors = db.Column(db.JSON, nullable=True)             # Stores list of strings
    ticket_budget = db.Column(db.String(255), nullable=True)
    attendance_barriers = db.Column(db.String(255), nullable=True)
    improvements_feedback = db.Column(db.Text, nullable=True)
    browsing_preference = db.Column(db.String(255), nullable=True)
    accessibility_importance = db.Column(db.String(255), nullable=True)

    def __init__(self, user_id=None, **kwargs):
        self.user_id = user_id
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def read(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "submitted_at": self.submitted_at.isoformat(),
            "organization": self.organization,
            "discovery_source": self.discovery_source,
            "visit_frequency": self.visit_frequency,
            "event_types_interested": self.event_types_interested or [],
            "attends_with": self.attends_with,
            "main_reason": self.main_reason,
            "travel_distance": self.travel_distance,
            "discovery_channels": self.discovery_channels or [],
            "decision_factors": self.decision_factors or [],
            "ticket_budget": self.ticket_budget,
            "attendance_barriers": self.attendance_barriers,
            "improvements_feedback": self.improvements_feedback,
            "browsing_preference": self.browsing_preference,
            "accessibility_importance": self.accessibility_importance
        }

    def create(self):
        db.session.add(self)
        db.session.commit()
        return self