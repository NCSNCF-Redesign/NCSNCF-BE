from datetime import datetime
from __init__ import db


class Media(db.Model):
    __tablename__ = 'media'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(512), nullable=False)

    # Descriptive metadata
    alt_text = db.Column(db.String(255), default='', nullable=False)
    caption = db.Column(db.String(500), default='', nullable=False)
    description = db.Column(db.Text, default='', nullable=False)

    # Upload tracking
    date_uploaded = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    uploader_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    uploader = db.relationship('User', backref=db.backref('uploaded_media', lazy=True))

    # File metadata (images)
    file_type = db.Column(db.String(50), nullable=False)   # e.g. 'image/jpeg', 'image/png', 'image/webp'
    file_size = db.Column(db.Integer, nullable=False)      # size in bytes
    width = db.Column(db.Integer, nullable=True)           # pixels
    height = db.Column(db.Integer, nullable=True)          # pixels

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'url': self.url,
            'alt_text': self.alt_text,
            'caption': self.caption,
            'description': self.description,
            'date_uploaded': self.date_uploaded.isoformat() if self.date_uploaded else None,
            'uploader': {
                'id': self.uploader.id,
                'name': getattr(self.uploader, 'name', None) or getattr(self.uploader, 'uid', 'Admin')
            } if self.uploader else None,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'dimensions': {
                'width': self.width,
                'height': self.height,
                'label': f"{self.width}x{self.height}" if self.width and self.height else None
            }
        }