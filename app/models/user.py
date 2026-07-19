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

    assignments = db.relationship(
        "Assignment",
        back_populates="student",
        cascade="all, delete"
    )