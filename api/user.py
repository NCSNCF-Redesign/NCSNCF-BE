import base64
import hashlib
import hmac
import jwt
import threading
import os

from flask import Blueprint, request, jsonify, current_app, Response, g
from flask_restful import Api, Resource
from datetime import datetime, timedelta

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from __init__ import app, db

limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri="memory://"
)

from api.authorize import token_required
from model.user import User, meets_password_rule, WeakPasswordError
from model import account_types
from model.google_token import verified_google_email
from model.github import GitHubUser

user_api = Blueprint('user_api', __name__, url_prefix='/api')
api = Api(user_api)

_consumed_reset_tokens = {}
_consumed_reset_tokens_lock = threading.Lock()

def _verify_reset_token(uid, token):
    if not uid or not token:
        return False, None
    parts = token.split('.')
    if len(parts) != 4:
        return False, None
    _uid_b64, exp_str, nonce, signature = parts
    try:
        exp = int(exp_str)
    except ValueError:
        return False, None
    if datetime.utcnow().timestamp() > exp:
        return False, None
    secret = current_app.config.get('RESET_TOKEN_SECRET')
    if not secret:
        return False, None
    payload = f"{uid}.{exp}.{nonce}".encode('utf-8')
    expected_sig = base64.urlsafe_b64encode(
        hmac.new(secret.encode('utf-8'), payload, hashlib.sha256).digest()
    ).decode('utf-8').rstrip('=')
    return hmac.compare_digest(expected_sig, signature), exp

def _consume_reset_token(uid, token):
    valid, exp = _verify_reset_token(uid, token)
    if not valid:
        return False
    now = datetime.utcnow().timestamp()
    with _consumed_reset_tokens_lock:
        for stored_token, stored_exp in list(_consumed_reset_tokens.items()):
            if stored_exp <= now:
                del _consumed_reset_tokens[stored_token]
        if token in _consumed_reset_tokens:
            return False
        _consumed_reset_tokens[token] = exp
        return True

def _staff_caller():
    probe = token_required(account_types.staff_roles())(lambda: g.current_user)
    caller = probe()
    return caller if isinstance(caller, User) else None

def _without_password(user_data):
    user_data.pop('password', None)
    return user_data


class _ID(Resource): 
    @token_required()
    def get(self):
        current_user = g.current_user
        user_data = _without_password(current_user.read())
        user_data['role'] = current_user.role
        user_data['is_admin'] = current_user.is_admin()
        user_data['is_teacher'] = current_user.is_teacher()
        return jsonify(user_data)

class _BULK(Resource): 
    def post(self):
        users = request.get_json()
        if not isinstance(users, list):
            return {'message': 'Expected a list of user data'}, 400
        results = {'errors': []}
        with current_app.test_client() as client:
            for user in users:
                user["password"] = app.config['DEFAULT_PASSWORD']
                response = client.post('/api/user', json=user)
                if response.status_code != 200:
                    results['errors'].append(response.get_json())
                continue
        return jsonify(results)

class _CRUD(Resource): 
    def post(self): 
        body = request.get_json()
        name = body.get('name')
        if name is None or len(name) < 2:
            return {'message': 'Name is missing, or is less than 2 characters'}, 400
        
        uid = body.get('uid')
        if uid is None or len(uid) < 2:
            return {'message': 'User ID is missing, or is less than 2 characters'}, 400
        
        staff = _staff_caller()
        if staff is None:
            _, status = GitHubUser().get(uid)
            if status != 200:
                return {'message': f'User ID {uid} not a valid GitHub account'}, 404
        
        account_type = account_types.get(body.get('accountType'))
        role = account_type['role']
        domains = account_type['google_verified_domains']
        verified_email = verified_google_email(body.get('idToken'), domains) if domains else False
        
        password = body.get('password')
        if password is not None:
            user_obj = User(name=name, uid=uid, password=password, role=role)
        else:
            user_obj = User(name=name, uid=uid, role=role)
            
        cleaned_body = {
            'name': name,
            'uid': uid,
            'password': password,
            'email': body.get('email')
        }
        
        if body.get('sid'):
            cleaned_body['sid'] = body.get('sid')
        if body.get('school'):
            cleaned_body['school'] = body.get('school')
        if body.get('class') is not None:
            cleaned_body['class'] = body.get('class')
        if body.get('game_profile') is not None:
            cleaned_body['game_profile'] = body.get('game_profile')
            
        cleaned_body = {k: v for k, v in cleaned_body.items() if v is not None}
        
        try:
            user = user_obj.create(cleaned_body) 
            if not user:
                db_user = User.query.filter_by(_uid=uid).first()
                if db_user:
                    return jsonify(_without_password(db_user.read())) 
                else:
                    return {'message': f'Processed {name}, either a format error or User ID duplicate'}, 400
            
            if verified_email:
                user.activate()
                
            if staff is not None:
                current_app.logger.info("AUDIT signup uid=%r created by staff uid=%r without a GitHub check", user.uid, staff.uid)
                
            return jsonify(_without_password(user.read()))
        except Exception as e:
            return {'message': f'Error creating user: {str(e)}'}, 500

    @token_required()
    def get(self):
        current_user = g.current_user
        page = request.args.get('page', type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 200)
        
        if page:
            pagination = User.query.paginate(page=page, per_page=per_page, error_out=False)
            users = pagination.items
            has_next = pagination.has_next
            has_prev = pagination.has_prev
            total = pagination.total
        else:
            users = User.query.all() 
            has_next = False
            has_prev = False
            total = len(users)
            
        json_ready = []
        for user in users:
            user_data = _without_password(user.read())
            if current_user.is_admin() or current_user.id == user.id:
                user_data['access'] = ['rw'] 
            else:
                user_data['access'] = ['ro'] 
            json_ready.append(user_data)
            
        if page:
            return jsonify({
                'users': json_ready,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'has_next': has_next,
                    'has_prev': has_prev
                }
            })
        else:
            return jsonify(json_ready)

    @token_required()
    def put(self):
        current_user = g.current_user
        body = request.get_json()
        
        if current_user.is_admin():
            uid = body.get('uid')
            if uid is None or uid == current_user.uid:
                user = current_user
            else: 
                user = User.query.filter_by(_uid=uid).first()
                if user is None:
                    return {'message': f'User {uid} not found'}, 404
        else:
            user = current_user
            
        if body.get('uid') and body.get('uid') != user._uid:
            _, status = GitHubUser().get(body.get('uid'))
            if status != 200:
                return {'message': f'User ID {body.get("uid")} not a valid GitHub account'}, 404
                
        user.update(body)
        return jsonify(_without_password(user.read()))

    @token_required(account_types.admin_role())
    def delete(self):
        body = request.get_json()
        uid = body.get('uid')
        user = User.query.filter_by(_uid=uid).first()
        
        if user is None:
            return {'message': f'User {uid} not found'}, 404
            
        blocker = user.deletion_blocker(g.current_user)
        if blocker:
            return {'message': blocker[1]}, blocker[0]
            
        user_json = _without_password(user.read())
        user.delete()
        return f"Deleted user: {user_json}", 204 

class _Section(Resource): 
    @token_required()
    def get(self):
        current_user = g.current_user
        return jsonify(current_user.read_sections())

    @token_required()
    def post(self):
        current_user = g.current_user
        body = request.get_json()
        sections = body.get('sections')
        if sections is None or len(sections) == 0:
            return {'message': "No sections to add were provided"}, 400
        if not current_user.add_sections(sections):
            return {'message': f'1 or more sections failed to add'}, 404
        return jsonify(current_user.read_sections())

    @token_required()
    def put(self):
        current_user = g.current_user
        body = request.get_json()
        section_data = body.get('section')
        if not section_data:
            return {'message': 'Section data is required'}, 400
        if not section_data.get('abbreviation'):
            return {'message': 'Section abbreviation is required'}, 400
        if not section_data.get('year'):
            return {'message': 'Section year is required'}, 400
            
        if not current_user.update_section(section_data):
            return {'message': 'Section not found or update failed'}, 404
        return jsonify(current_user.read_sections())

    @token_required()
    def delete(self):
        current_user = g.current_user
        body = request.get_json()
        sections = body.get('sections')
        if sections is None or len(sections) == 0:
            return {'message': "No sections to delete were provided"}, 400
        if not current_user.remove_sections(sections):
            return {'message': '1 or more sections failed to delete'}, 404
        return {'message': 'Sections deleted successfully'}, 200

class _Security(Resource):
    method_decorators = [limiter.limit("5 per minute")]
    def post(self):
        try:
            body = request.get_json()
            if not body:
                return {
                    "message": "Please provide user details",
                    "data": None,
                    "error": "Bad request"
                }, 400
            uid = body.get('uid')
            if uid is None:
                return {'message': 'User ID is missing'}, 401
            password = body.get('password')
            if not password:
                return {'message': 'Password is missing'}, 401
                
            user = User.query.filter_by(_uid=uid).first()
            if user is None or not user.is_password(password):
                return {'message': 'Invalid user id or password'}, 401
                
            if user:
                try:
                    token = jwt.encode(
                        {
                            "_uid": user._uid,
                            "token_version": user.token_version,
                            "exp": datetime.utcnow() + timedelta(seconds=current_app.config["JWT_TOKEN_MAX_AGE"]),
                        },
                        current_app.config["SECRET_KEY"],
                        algorithm="HS256"
                    )
                    is_production = os.environ.get('IS_PRODUCTION', 'false').lower() == 'true'
                    state = user.verification_state
                    response_data = {
                        "message": f"Authentication for {user._uid} successful",
                        "user": {
                            "uid": user._uid,
                            "name": user.name,
                            "role": user.role,
                            "class": user._class if getattr(user, '_class', None) is not None else [],
                            "active": user.active,
                            "verification_state": state,
                            "verification_required": state == "active_verification_required",
                            "verified_by_google": bool(account_types.google_domains(user.role))
                        }
                    }
                    resp = jsonify(response_data)
                    if is_production:
                        resp.set_cookie(
                            current_app.config["JWT_TOKEN_NAME"],
                            token,
                            max_age=current_app.config["JWT_TOKEN_MAX_AGE"],
                            secure=True,
                            httponly=True,
                            path='/',
                            samesite='None',
                            domain='.opencodingsociety.com'
                        )
                    else:
                        resp.set_cookie(
                            current_app.config["JWT_TOKEN_NAME"],
                            token,
                            max_age=current_app.config["JWT_TOKEN_MAX_AGE"],
                            secure=False,
                            httponly=True, 
                            path='/',
                            samesite='Lax'
                        )
                    return resp
                except Exception as e:
                    return {
                        "error": "Something went wrong",
                        "message": str(e)
                    }, 500
        except Exception as e:
            return {
                "message": "Something went wrong!",
                "error": str(e),
                "data": None
            }, 500

class _GradeData(Resource):
    @token_required()
    def get(self):
        current_user = g.current_user
        uid = request.args.get('uid')
        if current_user.is_admin() and uid:
            user = User.query.filter_by(_uid=uid).first()
            if not user:
                return {'message': f'User {uid} not found'}, 404
        else:
            user = current_user 
        return jsonify({'uid': user.uid, 'grade_data': user.grade_data})

    @token_required()
    def post(self):
        current_user = g.current_user
        body = request.get_json()
        uid = body.get('uid')
        if current_user.is_admin() and uid:
            user = User.query.filter_by(_uid=uid).first()
            if not user:
                return {'message': f'User {uid} not found'}, 404
        else:
            if uid and uid != current_user.uid and not current_user.is_admin():
                return {'message': 'Permission denied: You can only update your own grade data'}, 403
            user = current_user
            
        grade_data = body.get('grade_data')
        if not grade_data:
            return {'message': 'Grade data is missing'}, 400
        user.update({'grade_data': grade_data})
        return jsonify({'message': 'Grade data updated successfully', 'uid': user.uid, 'grade_data': user.grade_data})

class _APExam(Resource):
    @token_required()
    def get(self):
        current_user = g.current_user
        uid = request.args.get('uid')
        if current_user.is_admin() and uid:
            user = User.query.filter_by(_uid=uid).first()
            if not user:
                return {'message': f'User {uid} not found'}, 404
        else:
            user = current_user 
        return jsonify({'uid': user.uid, 'ap_exam': user.ap_exam})

    @token_required()
    def post(self):
        current_user = g.current_user
        body = request.get_json()
        uid = body.get('uid')
        if current_user.is_admin() and uid:
            user = User.query.filter_by(_uid=uid).first()
            if not user:
                return {'message': f'User {uid} not found'}, 404
        else:
            if uid and uid != current_user.uid and not current_user.is_admin():
                return {'message': 'Permission denied: You can only update your own AP exam data'}, 403
            user = current_user
            
        ap_exam = body.get('ap_exam')
        if not ap_exam:
            return {'message': 'AP exam data is missing'}, 400
        user.update({'ap_exam': ap_exam})
        return jsonify({'message': 'AP exam data updated successfully', 'uid': user.uid, 'ap_exam': user.ap_exam})

class _School(Resource):
    @token_required()
    def get(self):
        current_user = g.current_user
        uid = request.args.get('uid')
        if current_user.is_admin() and uid:
            user = User.query.filter_by(_uid=uid).first()
            if not user:
                return {'message': f'User {uid} not found'}, 404
        else:
            user = current_user 
        return jsonify({'uid': user.uid, 'school': user.school})

    @token_required()
    def post(self):
        current_user = g.current_user
        body = request.get_json()
        uid = body.get('uid')
        if current_user.is_admin() and uid:
            user = User.query.filter_by(_uid=uid).first()
            if not user:
                return {'message': f'User {uid} not found'}, 404
        else:
            if uid and uid != current_user.uid and not current_user.is_admin():
                return {'message': 'Permission denied: You can only update your own school data'}, 403
            user = current_user
            
        school = body.get('school')
        if not school:
            return {'message': 'School data is missing'}, 400
        user.update({'school': school})
        return jsonify({'message': 'School data updated successfully', 'uid': user.uid, 'school': user.school})

class _GuestCRUD(Resource):
    def post(self):
        body = request.get_json()
        uid = body.get('uid')
        if uid is None or len(uid) < 2:
            return {'message': 'Username is missing, or is less than 2 characters'}, 400
            
        password = body.get('password')
        name = f"Guest_{uid}"
        email = "?"
        sid = "?"
        school = "?"
        
        user_obj = User(name=name, uid=uid, password=password)
        cleaned_body = {
            'name': name,
            'uid': uid,
            'password': password,
            'email': email,
            'sid': sid,
            'school': school,
        }
        if body.get('class') is not None:
            cleaned_body['class'] = body.get('class')
            
        try:
            user = user_obj.create(cleaned_body)
            if not user:
                db_user = User.query.filter_by(_uid=uid).first()
                if db_user:
                    return jsonify(_without_password(db_user.read()))
                else:
                    return {'message': f'Failed to create guest account for {uid}'}, 400
            return jsonify(_without_password(user.read()))
        except Exception as e:
            return {'message': f'Error creating guest user: {str(e)}'}, 500

class _ResetPasswordVerified(Resource):
    def post(self):
        body = request.get_json(silent=True) or {}
        uid = body.get('uid')
        reset_token = body.get('resetToken')
        password = body.get('newPassword')
        if not uid or not reset_token or not password:
            return {'message': 'uid, resetToken, and newPassword are required'}, 400
            
        if not meets_password_rule(password):
            raise WeakPasswordError()
            
        if not _consume_reset_token(uid, reset_token):
            return {'message': 'Invalid, expired, or already-used reset token'}, 403
            
        user = User.query.filter_by(_uid=uid).first()
        if user is None:
            return {'message': f'User {uid} not found'}, 404
            
        updated = user.update({'password': password})
        if updated is None:
            return {'message': f'Failed to reset password for {uid}'}, 500
        return {'message': f'Password reset for {uid}'}, 200

class _VerifyAccount(Resource):
    @token_required(account_types.staff_roles())
    def post(self, uid):
        target = User.query.filter_by(_uid=uid).first()
        if target is None:
            return {'message': f'User {uid} not found'}, 404
            
        days = account_types.fixed_verification_days(target.role)
        if days is None:
            body = request.get_json(silent=True)
            if body is not None and not isinstance(body, dict):
                return {'message': 'The body must be a JSON object such as {"days": 30}'}, 400
            days = (body or {}).get('days', account_types.default_verification_days())
            
        interval = account_types.verification_interval_days()
        if not isinstance(days, int) or isinstance(days, bool) or not 1 <= days <= interval:
            return {'message': f'days must be a whole number from 1 to {interval}'}, 400
        return jsonify(_without_password(target.activate(days).read()))

class _DeactivateAccount(Resource):
    @token_required(account_types.staff_roles())
    def post(self, uid):
        target = User.query.filter_by(_uid=uid).first()
        if target is None:
            return {'message': f'User {uid} not found'}, 404
            
        blocker = target.deactivation_blocker(g.current_user)
        if blocker:
            return {'message': blocker[1]}, blocker[0]
        return jsonify(_without_password(target.deactivate().read()))

class _ChangeRole(Resource):
    @token_required(account_types.staff_roles())
    def post(self, uid):
        target = User.query.filter_by(_uid=uid).first()
        if target is None:
            return {'message': f'User {uid} not found'}, 404
            
        body = request.get_json(silent=True)
        role = body.get('role') if isinstance(body, dict) else None
        blocker = target.role_change_blocker(g.current_user, role)
        if blocker:
            return {'message': blocker[1]}, blocker[0]
            
        target.role = role
        db.session.commit()
        return jsonify(_without_password(target.read()))

class _Reverify(Resource):
    @token_required()
    def post(self):
        user = g.current_user
        domains = account_types.google_domains(user.role)
        if not domains:
            return {'message': 'A Teacher or Admin verifies this account'}, 403
            
        if user.verification_state != "active_verification_required":
            return {'message': 'No verification is due'}, 409
            
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return {'message': 'The body must be a JSON object'}, 400
            
        if not verified_google_email(body.get('idToken'), domains):
            return {'message': 'Google could not verify a school account from this sign-in'}, 403
        return jsonify(_without_password(user.activate().read()))

class _AdminCreate(Resource):
    @token_required(account_types.staff_roles())
    def post(self):
        body = request.get_json(silent=True) or {}
        allowed = account_types.staff_created()
        role = allowed.get((body.get('accountType') or "").lower())
        name, uid, password = body.get('name'), body.get('uid'), body.get('password')
        
        if role is None:
            return {'message': f"accountType must be one of: {', '.join(allowed)}"}, 400
        if not name or not uid or not password:
            return {'message': 'name, uid and password are required'}, 400
            
        user = User(name=name, uid=uid, password=password, role=role).create(
            {'email': body['email']} if body.get('email') else None)
        if not user:
            return {'message': f'User ID {uid} is a duplicate or invalid'}, 400
        return jsonify(_without_password(user.read()))

class _Class(Resource):
    @token_required()
    def get(self):
        current_user = g.current_user
        uid = request.args.get('uid')
        if current_user.is_admin() and uid:
            user = User.query.filter_by(_uid=uid).first()
            if not user:
                return {'message': f'User {uid} not found'}, 404
        else:
            user = current_user
        return jsonify({'uid': user.uid, 'class': user._class if getattr(user, '_class', None) is not None else []})

    @token_required()
    def post(self):
        current_user = g.current_user
        body = request.get_json() or {}
        uid = body.get('uid')
        if current_user.is_admin() and uid:
            user = User.query.filter_by(_uid=uid).first()
            if not user:
                return {'message': f'User {uid} not found'}, 404
        else:
            user = current_user
            
        action = body.get('action', 'add') 
        if action == 'clear':
            user.update({'class': []})
            return {'message': f'Cleared classes for {user.uid}'}, 200
            
        classes = body.get('class') or body.get('classes')
        if not classes:
            return {'message': f'No classes provided to {action}'}, 400
        if isinstance(classes, str):
            classes = [classes]
            
        existing = user._class if getattr(user, '_class', None) is not None else []
        
        if action == 'add':
            new_list = existing + [c for c in classes if c not in existing]
            user.update({'class': new_list})
            return jsonify({'uid': user.uid, 'class': user._class})
        elif action == 'remove':
            remaining = [c for c in existing if c not in classes]
            user.update({'class': remaining})
            return jsonify({'uid': user.uid, 'class': user._class})
        else:
            return {'message': f'Invalid action: {action}. Use "add", "remove", or "clear"'}, 400

    @token_required()
    def put(self):
        current_user = g.current_user
        body = request.get_json() or {}
        uid = body.get('uid')
        if current_user.is_admin() and uid:
            user = User.query.filter_by(_uid=uid).first()
            if not user:
                return {'message': f'User {uid} not found'}, 404
        else:
            user = current_user
            
        classes = body.get('class') or body.get('classes')
        if classes is None:
            return {'message': 'class list is required for PUT'}, 400
        if isinstance(classes, str):
            classes = [classes]
        user.update({'class': classes})
        return jsonify({'uid': user.uid, 'class': user._class})

# building RESTapi endpoint
api.add_resource(_ID, '/id')
api.add_resource(_BULK, '/users')
api.add_resource(_CRUD, '/user')
api.add_resource(_GuestCRUD, '/user/guest')
api.add_resource(_Section, '/user/section')
api.add_resource(_Security, '/authenticate')
api.add_resource(_GradeData, '/grade_data')
api.add_resource(_APExam, '/apexam')
api.add_resource(_School, '/school')
api.add_resource(_ResetPasswordVerified, '/reset-password')
api.add_resource(_VerifyAccount, '/user/<string:uid>/verify')
api.add_resource(_DeactivateAccount, '/user/<string:uid>/deactivate')
api.add_resource(_ChangeRole, '/user/<string:uid>/role')
api.add_resource(_Reverify, '/user/reverify')
api.add_resource(_AdminCreate, '/user/admin-create')
api.add_resource(_Class, '/user/class')