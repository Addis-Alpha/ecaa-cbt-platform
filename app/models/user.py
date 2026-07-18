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

    assignments = db.relationship(
        "Assignment",
        back_populates="student",
        cascade="all, delete"
    )