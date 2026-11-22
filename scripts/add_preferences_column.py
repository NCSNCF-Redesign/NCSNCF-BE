"""Add the NCSNCF/OCS preferences JSON column without deleting account data.
Run from the backend project root after making a backup and installing requirements:
    python scripts/add_preferences_column.py
Do not run scripts/db_init.py against an existing populated database.
"""
from sqlalchemy import inspect, text
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from __init__ import app, db
from model.user import User  # ensure metadata reflects new model

with app.app_context():
    engine = db.engine
    columns = {col['name'] for col in inspect(engine).get_columns('users')}
    if '_preferences' in columns:
        print('Already migrated: users._preferences exists')
    else:
        # SQLite accepts JSON as a declared type; MySQL has native JSON.
        with engine.begin() as connection:
            connection.execute(text('ALTER TABLE users ADD COLUMN _preferences JSON NULL'))
        print('Added users._preferences JSON NULL; existing rows preserved')
