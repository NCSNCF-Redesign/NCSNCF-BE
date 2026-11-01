from flask import Blueprint, request, jsonify
from flask_restful import Api, Resource
from flask_login import current_user
from __init__ import db
from model.survey import NCSNCFSurvey

survey_api = Blueprint('survey_api', __name__)
api = Api(survey_api)

class NCSNCFSurveyAPI(Resource):
    def post(self):
        body = request.get_json()
        if not body:
            return {"message": "No input data provided"}, 400

        # Validate mandatory fields
        required_fields = ['discovery_source', 'visit_frequency', 'main_reason']
        for field in required_fields:
            if not body.get(field):
                return {"message": f"Missing required field: {field}"}, 400

        # Authenticate user via Flask-Login
        user_id = current_user.id if current_user.is_authenticated else None
        if not user_id:
            return {"message": "User authentication required"}, 401

        # Check for an existing survey submission by this user
        survey = NCSNCFSurvey.query.filter_by(user_id=user_id).first()

        if survey:
            # Update existing user response
            survey.organization = body.get('organization', survey.organization)
            survey.discovery_source = body.get('discovery_source')
            survey.visit_frequency = body.get('visit_frequency')
            survey.interested_info = body.get('interested_info', [])
            survey.community_connection = body.get('community_connection', 'Unspecified')
            survey.main_reason = body.get('main_reason')
            survey.location = body.get('location', 'Unspecified')
            survey.find_methods = body.get('find_methods', [])
            survey.important_info = body.get('important_info', [])
            survey.cost_info = body.get('cost_info', [])
            survey.difficulties = body.get('difficulties', [])
            survey.improvements_feedback = body.get('improvements_feedback', '')
            survey.useful_features = body.get('useful_features', [])
            survey.browsing_preference = body.get('browsing_preference', 'Unspecified')
            survey.design_importance = body.get('design_importance', 'Unspecified')
            survey.ease_of_use = body.get('ease_of_use', 'Unspecified')
            survey.accessibility_features = body.get('accessibility_features', [])
            survey.learning_pref = body.get('learning_pref', [])
            survey.involvement_drivers = body.get('involvement_drivers', [])
        else:
            # Create a new survey record bound to user_id
            survey = NCSNCFSurvey(
                user_id=user_id,
                organization=body.get('organization', 'North County Special Needs Community Foundation'),
                discovery_source=body.get('discovery_source'),
                visit_frequency=body.get('visit_frequency'),
                interested_info=body.get('interested_info', []),
                community_connection=body.get('community_connection', 'Unspecified'),
                main_reason=body.get('main_reason'),
                location=body.get('location', 'Unspecified'),
                find_methods=body.get('find_methods', []),
                important_info=body.get('important_info', []),
                cost_info=body.get('cost_info', []),
                difficulties=body.get('difficulties', []),
                improvements_feedback=body.get('improvements_feedback', ''),
                useful_features=body.get('useful_features', []),
                browsing_preference=body.get('browsing_preference', 'Unspecified'),
                design_importance=body.get('design_importance', 'Unspecified'),
                ease_of_use=body.get('ease_of_use', 'Unspecified'),
                accessibility_features=body.get('accessibility_features', []),
                learning_pref=body.get('learning_pref', []),
                involvement_drivers=body.get('involvement_drivers', [])
            )

        try:
            db.session.add(survey)
            db.session.commit()
            return jsonify(survey.read())
        except Exception as e:
            db.session.rollback()
            return {"message": f"Database error: {str(e)}"}, 500

    def get(self):
        user_id = current_user.id if current_user.is_authenticated else None
        if not user_id:
            return {"message": "User authentication required"}, 401

        # Fetch only the logged-in user's survey record
        survey = NCSNCFSurvey.query.filter_by(user_id=user_id).first()
        if not survey:
            return {"message": "No survey found for current user"}, 404

        return jsonify(survey.read())

api.add_resource(NCSNCFSurveyAPI, '/api/profile/ncsncf')