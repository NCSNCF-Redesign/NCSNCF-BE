import jwt
from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user
from model.survey import CCAESurvey, db
from model.user import User

survey_api = Blueprint('survey_api', __name__, url_prefix='/api/profile')

@survey_api.route('/ccae', methods=['POST'])
def save_ccae_survey():
    data = request.get_json()
    if not data:
        return jsonify({"message": "No JSON payload provided"}), 400

    user_id = None

    # Method A: Check Flask-Login Session Cookie
    if current_user and current_user.is_authenticated:
        user_id = current_user.id

    # Method B: Fallback to reading JWT Bearer Token from Authorization Header
    auth_header = request.headers.get('Authorization')
    if not user_id and auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            token_uid = payload.get('_uid') or payload.get('uid') or payload.get('get_id')
            token_id = payload.get('id')

            user = None
            if token_id:
                user = User.query.get(token_id)
            elif token_uid:
                user = User.query.filter_by(_uid=str(token_uid)).first()

            if user:
                user_id = user.id
                print(f"[SURVEY AUTH] Successfully authenticated user: {user.uid} (ID: {user.id}) via JWT")
        except Exception as e:
            print(f"[SURVEY AUTH ERROR] JWT decode failed: {e}")

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
        
        db.session.add(survey)
        db.session.commit()

        print(f"[SURVEY RECORD] Survey saved with user_id={user_id}")
        return jsonify({"message": "Survey submitted successfully", "user_id": user_id, "survey": survey.read()}), 201

    except Exception as e:
        db.session.rollback()
        print(f"[SURVEY ERROR] Database save failed: {e}")
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
        print(f"[SURVEY ERROR] Fetch results failed: {e}")
        return jsonify({"message": f"Server error: {str(e)}"}), 500