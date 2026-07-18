from app.extensions import db


class Attempt(db.Model):

    __tablename__ = "attempt"

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

    # NEW: links this attempt to the specific Assignment it came from.
    #
    # Previously Attempt was only linked by student_id + exam_id, so
    # reassigning the same exam to the same student had no way to
    # distinguish the new attempt from the old one -- the dashboard
    # would keep showing the old score forever.
    #
    # Nullable because:
    #   - historical rows created before this column existed won't
    #     have a value (backfilled where possible, see migration),
    #   - an admin can remove an assignment while the student is
    #     mid-exam (see exam_session.py); that attempt is still saved,
    #     just with no assignment_id.
    #
    # ondelete="SET NULL": if an admin removes an Assignment WITHOUT
    # checking "also delete score record", the Attempt row survives
    # but its assignment_id is cleared at the database level rather
    # than blocking the delete or silently cascading.
    assignment_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "assignment.id",
            ondelete="SET NULL"
        ),
        nullable=True
    )

    score = db.Column(
        db.Integer,
        nullable=False
    )

    percentage = db.Column(
        db.Float,
        nullable=False
    )

    passed = db.Column(
        db.Boolean,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )

    student = db.relationship(
        "User"
    )

    exam = db.relationship(
        "Exam"
    )

    assignment = db.relationship(
        "Assignment"
    )