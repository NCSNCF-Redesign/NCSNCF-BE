from flask import Blueprint, request, jsonify
from flask_login import current_user
from model.survey import CCAESurvey, db
from model.user import User

survey_api = Blueprint('survey_api', __name__, url_prefix='/api/profile')

@survey_api.route('/ccae', methods=['POST'])
def save_ccae_survey():
    data = request.get_json()
    if not data:
        return jsonify({"message": "No input data provided"}), 400

    # Determine user ID if logged in via session/token
    user_id = current_user.id if current_user and current_user.is_authenticated else None

    try:
        survey = CCAESurvey(
            user_id=user_id,
            organization=data.get('organization', 'California Center for the Arts, Escondido'),
            discovery_source=data.get('discovery_source'),
            visit_frequency=data.get('visit_frequency'),
            event_types_interested=data.get('event_types_interested', []),
            attends_with=data.get('attends_with'),
            main_reason=data.get('main_reason'),
            travel_distance=data.get('travel_distance'),
            discovery_channels=data.get('discovery_channels', []),
            decision_factors=data.get('decision_factors', []),
            ticket_budget=data.get('ticket_budget'),
            attendance_barriers=data.get('attendance_barriers'),
            improvements_feedback=data.get('improvements_feedback', ''),
            browsing_preference=data.get('browsing_preference'),
            accessibility_importance=data.get('accessibility_importance')
        )
        survey.create()
        return jsonify({"message": "Survey submitted successfully", "survey": survey.read()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Database error: {str(e)}"}), 500


@survey_api.route('/ccae/results', methods=['GET'])
def get_ccae_results():
    """Retrieve all survey results, joined with user UID if available."""
    try:
        surveys = CCAESurvey.query.order_by(CCAESurvey.submitted_at.desc()).all()
        results = []
        
        for survey in surveys:
            record = survey.read()
            if survey.user_id:
                user = User.query.get(survey.user_id)
                record['uid'] = user.uid if user else None
            else:
                record['uid'] = None
            results.append(record)

        return jsonify({"total_count": len(results), "results": results}), 200
    except Exception as e:
        return jsonify({"message": f"Server error: {str(e)}"}), 500