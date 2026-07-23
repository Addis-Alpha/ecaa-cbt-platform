from flask_login import UserMixin
from app.extensions import db


class User(
    UserMixin,
    db.Model
):

    __tablename__ = "user"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    username = db.Column(
        db.String(100),
        unique=True,
        nullable=True
    )

    student_id = db.Column(
        db.String(100),
        unique=True
    )

    full_name = db.Column(
        db.String(200)
    )

    password = db.Column(
        db.String(300)
    )

    role = db.Column(
        db.String(20)
    )

    organization = db.Column(
        db.String(200)
    )

    job_title = db.Column(
        db.String(200)
    )

    is_super_admin = db.Column(
        db.Boolean,
        default=False
    )

    must_change_password = db.Column(
        db.Boolean,
        default=False
    )

    # Tracks whether this user currently has an active logged-in
    # session, and which one. None = no active session (safe to log
    # in). Set on login, cleared on logout (auth.py:logout), by an
    # admin's Force Logout action (admin.py:force_logout), or
    # automatically by the inactivity timeout (see
    # enforce_single_session in app/__init__.py).
    active_session_token = db.Column(
        db.String(100),
        nullable=True
    )

    # NEW: timestamp of this user's most recent page request while
    # logged in. Updated on every authenticated request (see
    # enforce_single_session in app/__init__.py). Used to auto-clear
    # active_session_token after 20 minutes of inactivity -- covers
    # a student closing the tab, losing power, or losing network
    # without ever hitting the real /logout route.
    last_activity = db.Column(
        db.DateTime,
        nullable=True
    )

    assignments = db.relationship(
        "Assignment",
        back_populates="student",
        cascade="all, delete"
    )