from flask import (
    Blueprint,
    render_template,
    request,
    abort,
)

from flask_login import (
    login_required,
    current_user,
)

from app.extensions import db
from app.models.attempt import Attempt
from app.models.user import User
from app.models.exam import Exam
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
        abort(403)

    # NEW: search/filter by examinee (ID, name, organization, job
    # title) or examination (code, title).
    # GET /results?q=keyword -- case-insensitive, matches any of
    # those fields. Empty/omitted "q" behaves exactly as before (full
    # list). Joins are only added when actually searching, so the
    # unfiltered case stays as cheap as it was before.
    search = request.args.get(
        "q",
        ""
    ).strip()

    query = Attempt.query

    if search:

        like = f"%{search}%"

        query = (
            query
            .join(User, User.id == Attempt.student_id)
            .join(Exam, Exam.id == Attempt.exam_id)
            .filter(
                db.or_(
                    User.student_id.ilike(like),
                    User.full_name.ilike(like),
                    User.organization.ilike(like),
                    User.job_title.ilike(like),
                    Exam.code.ilike(like),
                    Exam.title.ilike(like),
                )
            )
        )

    attempts = query.order_by(
        Attempt.created_at.desc()
    ).all()

    app_logger.info(
        f"RESULTS VIEWED | "
        f"Admin={current_user.username}"
    )

    return render_template(
        "results.html",
        attempts=attempts,
        search=search,
    )


# ==========================
# STUDENT RESULT HISTORY
# ==========================

@results_bp.route("/my-results")
@login_required
def student_results():

    if current_user.role != "student":
        abort(403)

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