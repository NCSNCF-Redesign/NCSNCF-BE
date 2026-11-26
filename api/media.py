import os
import uuid
from PIL import Image
from flask import Blueprint, request, jsonify, current_app, url_for
from flask_login import current_user
from werkzeug.utils import secure_filename
from __init__ import db
from model.media import Media

media_api = Blueprint('media_api', __name__, url_prefix='/api/media')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
MIME_TYPES = {
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'webp': 'image/webp',
    'gif': 'image/gif',
}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@media_api.route('', methods=['GET'])
def list_media():
    items = Media.query.order_by(Media.date_uploaded.desc()).all()
    return jsonify([m.to_dict() for m in items]), 200


@media_api.route('', methods=['POST'])
def upload_media():
    if not current_user.is_authenticated or not current_user.is_admin():
        return jsonify({'error': 'Admin login required'}), 403

    if 'file' not in request.files:
        return jsonify({'error': 'No file part in request'}), 400

    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Only image files (PNG, JPG, WEBP, GIF) are allowed'}), 400

    ext = file.filename.rsplit('.', 1)[1].lower()

    try:
        img = Image.open(file.stream)
        img.verify()
        file.stream.seek(0)
        img = Image.open(file.stream)
        width, height = img.size
        file.stream.seek(0)
    except Exception:
        return jsonify({'error': 'Invalid or corrupted image file'}), 400

    file.stream.seek(0, os.SEEK_END)
    file_size = file.stream.tell()
    file.stream.seek(0)

    safe_original = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex}_{safe_original}"
    upload_dir = os.path.join(current_app.static_folder, 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    file.save(os.path.join(upload_dir, unique_name))

    public_url = url_for('static', filename=f'uploads/{unique_name}', _external=True)

    media = Media(
        filename=safe_original,
        url=public_url,
        alt_text=request.form.get('alt_text', '').strip(),
        caption=request.form.get('caption', '').strip(),
        description=request.form.get('description', '').strip(),
        uploader_id=current_user.id,
        file_type=file.mimetype or MIME_TYPES.get(ext, 'image/jpeg'),
        file_size=file_size,
        width=width,
        height=height,
    )
    db.session.add(media)
    db.session.commit()

    return jsonify(media.to_dict()), 201


@media_api.route('/<int:media_id>', methods=['PATCH', 'PUT'])
def update_media(media_id):
    if not current_user.is_authenticated or not current_user.is_admin():
        return jsonify({'error': 'Admin login required'}), 403

    media = Media.query.get_or_404(media_id)
    data = request.get_json() or {}

    for field in ('alt_text', 'caption', 'description'):
        if field in data:
            setattr(media, field, str(data[field]).strip())

    db.session.commit()
    return jsonify(media.to_dict()), 200


@media_api.route('/<int:media_id>', methods=['DELETE'])
def delete_media(media_id):
    if not current_user.is_authenticated or not current_user.is_admin():
        return jsonify({'error': 'Admin login required'}), 403

    media = Media.query.get_or_404(media_id)
    local_path = os.path.join(current_app.static_folder, 'uploads', os.path.basename(media.url))
    if os.path.exists(local_path):
        os.remove(local_path)

    db.session.delete(media)
    db.session.commit()
    return jsonify({'message': 'Deleted'}), 200