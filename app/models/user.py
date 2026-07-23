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

    # NEW: required for examinees (enforced in students.py at the
    # route level, same pattern as the existing fields above -- none
    # of them use nullable=False either, they rely on form/route
    # validation rather than a DB constraint). Nullable at the DB
    # level on purpose, so this doesn't break on deploy: existing
    # examinee rows just have NULL here until an admin edits them.
    organization = db.Column(
        db.String(200)
    )

    job_title = db.Column(
        db.String(200)
    )

    # NEW: distinguishes a super admin (can create/edit/delete other
    # admin accounts) from a regular admin (everything else -- exams,
    # questions, examinees, assignments, results -- is unaffected by
    # this flag, since those checks all just test role == "admin").
    # Defaults to False so existing admin rows are safe after the
    # migration; promote the first one manually (see migration file).
    is_super_admin = db.Column(
        db.Boolean,
        default=False
    )

    # NEW: forces a password change on next login. Set True for the
    # auto-created default admin (see app/seed.py) since it starts
    # with a fixed, publicly-known password. Cleared automatically
    # once the user successfully changes their password (see
    # auth.py:change_password). Enforced app-wide by a before_request
    # hook in app/__init__.py -- while this is True, every page except
    # the change-password page itself redirects back to it.
    must_change_password = db.Column(
        db.Boolean,
        default=False
    )

    # NEW: tracks whether this user currently has an active logged-in
    # session, and which one. None = no active session (safe to log
    # in). When set, it's a random token that must match the token
    # stored in the browser's session cookie -- if they don't match
    # (e.g. an admin force-logged the user out, or a second login was
    # blocked and somehow proceeded anyway), the before_request hook
    # in app/__init__.py force-logs-out that browser. Cleared on
    # logout (see auth.py:logout) or by an admin's "force logout"
    # action.
    active_session_token = db.Column(
        db.String(100),
        nullable=True
    )

    assignments = db.relationship(
        "Assignment",
        back_populates="student",
        cascade="all, delete"
    )