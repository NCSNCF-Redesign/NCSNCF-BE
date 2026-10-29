from datetime import datetime
from __init__ import db

class NCSNCFSurvey(db.Model):
    __tablename__ = 'ncsncf_surveys'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Metadata & Base Info
    organization = db.Column(db.String(255), nullable=False, default="North County Special Needs Community Foundation")
    
    # Survey Questions 1-18
    discovery_source = db.Column(db.String(255), nullable=True)        # Q1
    visit_frequency = db.Column(db.String(255), nullable=True)         # Q2
    interested_info = db.Column(db.JSON, nullable=True)                 # Q3 (List)
    community_connection = db.Column(db.String(255), nullable=True)    # Q4
    main_reason = db.Column(db.String(255), nullable=True)             # Q5
    location = db.Column(db.String(255), nullable=True)                # Q6
    find_methods = db.Column(db.JSON, nullable=True)                    # Q7 (List)
    important_info = db.Column(db.JSON, nullable=True)                  # Q8 (List)
    cost_info = db.Column(db.JSON, nullable=True)                       # Q9 (List)
    difficulties = db.Column(db.JSON, nullable=True)                    # Q10 (List)
    improvements_feedback = db.Column(db.Text, nullable=True)          # Q11 (Free Text)
    useful_features = db.Column(db.JSON, nullable=True)                 # Q12 (List)
    browsing_preference = db.Column(db.String(255), nullable=True)      # Q13
    design_importance = db.Column(db.String(255), nullable=True)        # Q14
    ease_of_use = db.Column(db.String(255), nullable=True)              # Q15
    accessibility_features = db.Column(db.JSON, nullable=True)         # Q16 (List)
    learning_pref = db.Column(db.JSON, nullable=True)                  # Q17 (List)
    involvement_drivers = db.Column(db.JSON, nullable=True)             # Q18 (List)

    def __init__(self, user_id=None, **kwargs):
        self.user_id = user_id
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def read(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "organization": self.organization,
            "discovery_source": self.discovery_source,
            "visit_frequency": self.visit_frequency,
            "interested_info": self.interested_info or [],
            "community_connection": self.community_connection,
            "main_reason": self.main_reason,
            "location": self.location,
            "find_methods": self.find_methods or [],
            "important_info": self.important_info or [],
            "cost_info": self.cost_info or [],
            "difficulties": self.difficulties or [],
            "improvements_feedback": self.improvements_feedback or "",
            "useful_features": self.useful_features or [],
            "browsing_preference": self.browsing_preference,
            "design_importance": self.design_importance,
            "ease_of_use": self.ease_of_use,
            "accessibility_features": self.accessibility_features or [],
            "learning_pref": self.learning_pref or [],
            "involvement_drivers": self.involvement_drivers or []
        }

    def create(self):
        db.session.add(self)
        db.session.commit()
        return self