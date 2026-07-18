from app.extensions import db


class Question(db.Model):

    __tablename__ = "questions"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    exam_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "exam.id"
        ),
        nullable=False
    )

    question_text = db.Column(
        db.Text,
        nullable=False
    )

    option_a = db.Column(
        db.String(300),
        nullable=False
    )

    option_b = db.Column(
        db.String(300),
        nullable=False
    )

    option_c = db.Column(
        db.String(300),
        nullable=False
    )

    option_d = db.Column(
        db.String(300),
        nullable=False
    )

    correct_answer = db.Column(
        db.String(1),
        nullable=False
    )

    marks = db.Column(
        db.Integer,
        default=1
    )

    exam = db.relationship(
        "Exam",
        back_populates="questions"
    )