from flask import (
    Blueprint,
    render_template,
    session,
)

from flask_login import (
    login_required,
    current_user,
)

from app.models.assignment import Assignment
from app.models.attempt import Attempt
from app.logger import app_logger


student_bp = Blueprint(
    "student",
    __name__,
)


# ==========================
# STUDENT DASHBOARD
# ==========================

@student_bp.route("/student/dashboard")
@login_required
def student_dashboard():

    if current_user.role != "student":
        return "Access denied", 403

    # NEW: completed assignments are now deleted automatically the
    # moment the exam is finished (see exam_session.py:save_attempt),
    # so anything left in Assignment for this student is genuinely
    # still pending. Older completed rows that predate this change
    # (if any weren't cleaned up yet) are filtered out defensively.
    pending_assignments = [
        a for a in Assignment.query.filter_by(
            student_id=current_user.id
        ).all()
        if not a.completed
    ]

    # NEW: "Completed" cards are now built from Attempt, not
    # Assignment, since the assignment row no longer exists once the
    # exam is done. Only attempts completed DURING THIS LOGIN SESSION
    # are shown here -- the list is reset to empty on every fresh
    # login (see auth.py) and appended to the moment an attempt is
    # saved (see exam_session.py). This has no effect on the actual
    # score data; Result History always shows every attempt
    # regardless of this list.
    completed_this_session = session.get(
        "completed_this_session", []
    )

    completed_attempts = []

    if completed_this_session:

        completed_attempts = Attempt.query.filter(
            Attempt.id.in_(completed_this_session),
            Attempt.student_id == current_user.id,
        ).all()

    # Build one unified list of dashboard cards, sorted by exam code
    # so pending and completed cards for different exams interleave
    # predictably instead of pending-always-first.
    cards = []

    for a in pending_assignments:

        cards.append({
            "status": "pending",
            "exam": a.exam,
            "assignment_id": a.id,
            "attempt": None,
        })

    for attempt in completed_attempts:

        cards.append({
            "status": "completed",
            "exam": attempt.exam,
            "assignment_id": None,
            "attempt": attempt,
        })

    cards.sort(key=lambda c: c["exam"].code)

    app_logger.info(
        f"STUDENT DASHBOARD | "
        f"StudentID={current_user.student_id}"
    )

    return render_template(
        "student_dashboard.html",
        cards=cards,
    )