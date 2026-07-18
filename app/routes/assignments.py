from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
)

from flask_login import (
    login_required,
    current_user,
)

from app.extensions import db
from app.models.user import User
from app.models.exam import Exam
from app.models.assignment import Assignment
from app.models.attempt import Attempt
from app.logger import app_logger


assignments_bp = Blueprint(
    "assignments",
    __name__,
)


# ==========================
# ASSIGN EXAM
# ==========================

@assignments_bp.route(
    "/assign",
    methods=["GET", "POST"],
)
@login_required
def assign_exam():

    if current_user.role != "admin":
        abort(403)

    if request.method == "POST":

        student_id = int(
            request.form.get("student")
        )

        exam_id = int(
            request.form.get("exam")
        )

        existing = Assignment.query.filter_by(
            student_id=student_id,
            exam_id=exam_id,
        ).first()

        if existing:

            flash(
                "Student is already assigned to this exam."
            )

        else:

            assignment = Assignment(
                student_id=student_id,
                exam_id=exam_id,
            )

            db.session.add(assignment)
            db.session.commit()

            student = User.query.get(student_id)
            exam = Exam.query.get(exam_id)

            app_logger.info(
                f"EXAM ASSIGNED | "
                f"Student={student.student_id} | "
                f"Exam={exam.code} | "
                f"By={current_user.username}"
            )

            flash(
                "Exam assigned successfully."
            )

        return redirect(
            url_for(
                "assignments.assign_exam"
            )
        )

    students = User.query.filter_by(
        role="student"
    ).order_by(
        User.full_name.asc()
    ).all()

    exams = Exam.query.order_by(
        Exam.code.asc()
    ).all()

    return render_template(
        "assign.html",
        students=students,
        exams=exams,
    )


# ==========================
# MANAGE / REMOVE ASSIGNMENTS
# ==========================

@assignments_bp.route(
    "/assignments/manage",
    methods=["GET"],
)
@login_required
def manage_assignments():

    if current_user.role != "admin":
        abort(403)

    # Assignment only stores student_id / exam_id (no ORM
    # relationships defined), so join explicitly to display names
    # instead of assuming assignment.student / assignment.exam exist.
    rows = (
        db.session.query(Assignment, User, Exam)
        .join(User, User.id == Assignment.student_id)
        .join(Exam, Exam.id == Assignment.exam_id)
        .order_by(Assignment.id.desc())
        .all()
    )

    # Attempt has no FK back to Assignment either (same pattern as
    # exam_session.py), so look attempts up the same way: by
    # student_id + exam_id. This lets the template show a score next
    # to completed assignments and offer the "also delete score"
    # checkbox only where an attempt actually exists.
    attempts = Attempt.query.all()

    attempt_lookup = {}

    for attempt in attempts:

        key = (attempt.student_id, attempt.exam_id)

        # If a student was ever allowed multiple attempts against the
        # same exam_id, keep the most recent one (highest id) for
        # display purposes.
        if (
            key not in attempt_lookup
            or attempt.id > attempt_lookup[key].id
        ):
            attempt_lookup[key] = attempt

    assignment_rows = []

    for assignment, student, exam in rows:

        attempt = attempt_lookup.get(
            (assignment.student_id, assignment.exam_id)
        )

        assignment_rows.append({
            "assignment": assignment,
            "student": student,
            "exam": exam,
            "attempt": attempt,
        })

    return render_template(
        "manage_assignments.html",
        assignment_rows=assignment_rows,
    )


@assignments_bp.route(
    "/assignments/remove/<int:id>",
    methods=["POST"],
)
@login_required
def remove_assignment(id):

    if current_user.role != "admin":
        abort(403)

    assignment = Assignment.query.get_or_404(id)

    student = User.query.get(assignment.student_id)
    exam = Exam.query.get(assignment.exam_id)

    # Admin decides per-removal whether to also wipe the score
    # record. Defaults to "no" -- the checkbox must be explicitly
    # checked to delete attempt history.
    delete_attempt = request.form.get("delete_attempt") == "on"

    removed_attempts = 0

    if delete_attempt:

        attempts = Attempt.query.filter_by(
            student_id=assignment.student_id,
            exam_id=assignment.exam_id,
        ).all()

        for attempt in attempts:

            db.session.delete(attempt)

            removed_attempts += 1

    db.session.delete(assignment)

    db.session.commit()

    app_logger.info(
        f"ASSIGNMENT REMOVED | "
        f"Student={student.student_id if student else assignment.student_id} | "
        f"Exam={exam.code if exam else assignment.exam_id} | "
        f"AttemptsDeleted={removed_attempts} | "
        f"By={current_user.username}"
    )

    if removed_attempts:

        flash(
            "Assignment removed and score record deleted. "
            "The student can be reassigned this exam."
        )

    else:

        flash(
            "Assignment removed. The student can be reassigned "
            "this exam."
        )

    return redirect(
        url_for(
            "assignments.manage_assignments"
        )
    )