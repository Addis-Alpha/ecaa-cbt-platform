from app.extensions import db

class Assignment(db.Model):

    __tablename__ = "assignment"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "user.id"
        ),
        nullable=False
    )

    exam_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "exam.id"
        ),
        nullable=False
    )

    completed = db.Column(
        db.Boolean,
        default=False
    )

    student = db.relationship(
        "User",
        back_populates="assignments"
    )

    exam = db.relationship(
        "Exam",
        back_populates="assignments"
    )