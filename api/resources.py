import json
import os
from flask import Blueprint, request, jsonify, g
from flask_restful import Api, Resource
from api.authorize import token_required

resources_api = Blueprint('resources_api', __name__, url_prefix='/api')
api = Api(resources_api)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'instance', 'data')
RESOURCES_FILE = os.path.join(DATA_DIR, 'resources.json')

def load_resources():
    if not os.path.exists(RESOURCES_FILE):
        return []
    try:
        with open(RESOURCES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_resources(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(RESOURCES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

class ResourcesListAPI(Resource):
    def get(self):
        """Public: returns all resources grouped by category."""
        return jsonify(load_resources())

    @token_required()
    def post(self):
        """Admin only: adds a new resource item to a category (or creates a category)."""
        current_user = g.current_user
        if not (current_user and current_user.is_admin()):
            return {'message': 'Admin privilege required'}, 403

        body = request.get_json() or {}
        category_name = body.get('category', '').strip()
        title = body.get('title', '').strip()
        url = body.get('url', '').strip()
        description = body.get('description', '').strip()
        phone = body.get('phone', '').strip()
        email = body.get('email', '').strip()

        if not category_name or not title:
            return {'message': 'category and title are required'}, 400

        data = load_resources()
        target_cat = None
        for cat in data:
            if cat.get('category', '').lower() == category_name.lower():
                target_cat = cat
                break

        if not target_cat:
            target_cat = {
                'category': category_name,
                'description': '',
                'items': []
            }
            data.append(target_cat)

        new_item = {
            'title': title,
            'url': url,
            'description': description
        }
        if phone:
            new_item['phone'] = phone
        if email:
            new_item['email'] = email

        target_cat['items'].append(new_item)
        save_resources(data)
        return jsonify({'message': 'Resource added successfully', 'resources': data})

    @token_required()
    def delete(self):
        """Admin only: deletes a resource by category and title, or an entire category."""
        current_user = g.current_user
        if not (current_user and current_user.is_admin()):
            return {'message': 'Admin privilege required'}, 403

        body = request.get_json() or {}
        category_name = body.get('category', '').strip()
        title = body.get('title', '').strip()

        if not category_name:
            return {'message': 'category is required'}, 400

        data = load_resources()
        found = False
        for cat in data:
            if cat.get('category', '').lower() == category_name.lower():
                if title:
                    orig_len = len(cat.get('items', []))
                    cat['items'] = [it for it in cat.get('items', []) if it.get('title', '').lower() != title.lower()]
                    if len(cat['items']) < orig_len:
                        found = True
                else:
                    data = [c for c in data if c.get('category', '').lower() != category_name.lower()]
                    found = True
                    break

        if not found:
            return {'message': 'Resource not found'}, 404

        save_resources(data)
        return jsonify({'message': 'Resource removed successfully', 'resources': data})

api.add_resource(ResourcesListAPI, '/resources')
