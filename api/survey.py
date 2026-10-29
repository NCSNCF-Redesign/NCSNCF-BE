from flask import Blueprint, request, jsonify
from flask_restful import Api, Resource
from current_user_helper import g  # Adjust import based on your auth setup

ncsncf_api = Blueprint('ncsncf_api', __name__)
api = Api(ncsncf_api)

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

        user_id = getattr(g, 'current_user', None).id if hasattr(g, 'current_user') and g.current_user else None

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
            survey.create()
            return jsonify(survey.read())
        except Exception as e:
            db.session.rollback()
            return {"message": f"Database error: {str(e)}"}, 500

    def get(self):
        surveys = NCSNCFSurvey.query.all()
        return jsonify([s.read() for s in surveys])

api.add_resource(NCSNCFSurveyAPI, '/api/profile/ncsncf')