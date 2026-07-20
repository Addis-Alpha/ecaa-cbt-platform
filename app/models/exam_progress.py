from app.extensions import db


class ExamProgress(db.Model):
    """
    Server-side exam progress. Replaces the previous approach of
    storing question order / answers / current index in the Flask
    session cookie -- that lived only in the browser and wasn't
    reliably recoverable after a real power cut or crash (session
    cookies aren't guaranteed to survive a browser process dying).

    One row per (student, exam) while an attempt is in progress.
    Deleted the moment the attempt finishes (submitted or timed out)
    -- see exam_session.py.
    """

    __tablename__ = "exam_progress"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    exam_id = db.Column(
        db.Integer,
        db.ForeignKey("exam.id"),
        nullable=False
    )

    # Nullable + ON DELETE SET NULL for the same reason as
    # Attempt.assignment_id: an admin can remove the assignment while
    # the student is mid-exam, and that student is still allowed to
    # finish (see exam_session.py). This progress row shouldn't be
    # destroyed just because the assignment underneath it was removed.
    assignment_id = db.Column(
        db.Integer,
        db.ForeignKey("assignment.id", ondelete="SET NULL"),
        nullable=True
    )

    # List of question IDs in the randomized order shown to this
    # student, decided once at exam start and fixed for the rest of
    # the attempt.
    question_order = db.Column(
        db.JSON,
        nullable=False
    )

    # {"<question_id>": "<A/B/C/D>"} -- reassigned as a whole new dict
    # on every save (not mutated in place) so SQLAlchemy reliably
    # detects the change.
    answers = db.Column(
        db.JSON,
        nullable=False,
        default=dict
    )

    current_index = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    # Absolute timestamp, not a duration -- computed once at start as
    # (start time + exam.duration_minutes). Storing an absolute end
    # time rather than "seconds remaining" is what makes recovery
    # correct: however long the student was disconnected, resuming
    # just recomputes (end_time - now) rather than resetting a timer.
    end_time = db.Column(
        db.DateTime,
        nullable=False
    )

    started_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )

    student = db.relationship("User")
    exam = db.relationship("Exam")

    __table_args__ = (
        db.UniqueConstraint(
            "student_id",
            "exam_id",
            name="uq_exam_progress_student_exam",
        ),
    )