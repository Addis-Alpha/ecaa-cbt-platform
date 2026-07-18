from app.extensions import db


class Exam(db.Model):

    __tablename__ = "exam"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    code = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    title = db.Column(
        db.String(200),
        nullable=False
    )

    duration_minutes = db.Column(
        db.Integer,
        nullable=False
    )

    pass_mark = db.Column(
        db.Integer,
        nullable=False
    )

    questions = db.relationship(
        "Question",
        back_populates="exam",
        cascade="all, delete"
    )

    assignments = db.relationship(
        "Assignment",
        back_populates="exam",
        cascade="all, delete"
    )