from flask import (
    Blueprint,
    render_template,
)

from flask_login import (
    login_required,
    current_user,
)

from app.models.attempt import Attempt
from app.logger import app_logger


results_bp = Blueprint(
    "results",
    __name__
)

# ==========================
# ADMIN RESULT HISTORY
# ==========================

@results_bp.route("/results")
@login_required
def results():

    if current_user.role != "admin":
        return "Access denied"

    attempts = (
        Attempt.query
        .order_by(Attempt.created_at.desc())
        .all()
    )

    app_logger.info(
        f"RESULTS VIEWED | "
        f"Admin={current_user.username}"
    )

    return render_template(
        "results.html",
        attempts=attempts
    )


# ==========================
# STUDENT RESULT HISTORY
# ==========================

@results_bp.route("/my-results")
@login_required
def student_results():

    if current_user.role != "student":
        return "Access denied"

    attempts = (
        Attempt.query
        .filter_by(student_id=current_user.id)
        .order_by(Attempt.created_at.desc())
        .all()
    )

    app_logger.info(
        f"MY RESULTS VIEWED | "
        f"Student={current_user.student_id}"
    )

    return render_template(
        "student_results.html",
        attempts=attempts
    )