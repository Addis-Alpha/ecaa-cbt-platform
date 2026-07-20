from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    make_response,
    abort
)

from flask_login import (
    login_required,
    current_user,
)

from app.extensions import db

from app.models.exam import Exam
from app.models.question import Question
from app.models.assignment import Assignment
from app.models.attempt import Attempt
from app.models.exam_progress import ExamProgress

from app.logger import app_logger

import random
from datetime import datetime, timedelta


exam_session_bp = Blueprint(
    "exam_session",
    __name__,
)


# ======================================================
# Helper Functions
# ======================================================

def get_progress(student_id, exam_id):

    return ExamProgress.query.filter_by(
        student_id=student_id,
        exam_id=exam_id,
    ).first()


def create_progress(student_id, exam_id, assignment_id, questions, duration_minutes):
    """
    Called exactly once, the first time a student opens an exam --
    decides the randomized question order and the absolute end time,
    then persists both to the database immediately. Every subsequent
    request (even after a crash/disconnect) reads this same row
    rather than recomputing anything.
    """

    ids = [q.id for q in questions]
    random.shuffle(ids)

    progress = ExamProgress(
        student_id=student_id,
        exam_id=exam_id,
        assignment_id=assignment_id,
        question_order=ids,
        answers={},
        current_index=0,
        end_time=datetime.now() + timedelta(minutes=duration_minutes),
    )

    db.session.add(progress)
    db.session.commit()

    return progress


def clear_progress(progress):

    db.session.delete(progress)
    db.session.commit()


def score_exam(questions, answers):
    """
    Shared scoring logic so start_exam and the timeout branch
    can't drift apart. Returns (score, total, percentage).
    """

    score = 0
    total = 0

    for question in questions:

        total += question.marks

        student_answer = answers.get(
            str(question.id)
        )

        if student_answer == question.correct_answer:

            score += question.marks

    percentage = 0

    if total > 0:

        percentage = round(
            (score / total) * 100,
            1
        )

    return score, total, percentage


def save_attempt(exam, score, total, percentage, assignment):
    """
    Persists the Attempt row, then removes the Assignment now that
    it's fulfilled -- so the admin no longer has to manually delete
    a completed assignment before reassigning the same exam.

    "assignment" may be None if the admin already removed it while
    the student was mid-exam -- the student is still allowed to
    finish, there's just no Assignment row to clean up.
    """

    passed = percentage >= exam.pass_mark

    attempt = Attempt(
        student_id=current_user.id,
        exam_id=exam.id,
        assignment_id=(assignment.id if assignment is not None else None),
        score=score,
        percentage=percentage,
        passed=passed
    )

    db.session.add(attempt)
    db.session.commit()

    # Record that THIS ATTEMPT belongs to the current login session.
    # The dashboard only shows a "Completed" card for attempts in
    # this list; it's reset to empty on every fresh login (see
    # auth.py) and appended to here. Purely cosmetic dashboard
    # behavior -- unrelated to exam progress recovery, which is what
    # ExamProgress (above) exists for.
    completed_ids = session.get("completed_this_session", [])

    if attempt.id not in completed_ids:
        completed_ids.append(attempt.id)

    session["completed_this_session"] = completed_ids
    session.modified = True

    # Auto-remove the assignment now that it's been fulfilled.
    if assignment is not None:

        db.session.delete(assignment)
        db.session.commit()

    return passed


# ======================================================
# START EXAM
# ======================================================

@exam_session_bp.route(
    "/exam/start/<int:id>",
    methods=["GET", "POST"]
)
@login_required
def start_exam(id):

    # ------------------------------------
    # Only students may take exams
    # ------------------------------------

    if current_user.role != "student":
        abort(403)

    # ------------------------------------
    # Load exam
    # ------------------------------------

    exam = Exam.query.get_or_404(id)

    # ------------------------------------
    # Verify assignment / existing progress
    # ------------------------------------
    #
    # An admin can remove an assignment at any time, including while
    # the student is mid-exam. A student who is already mid-exam
    # (i.e. has an ExamProgress row for this exam) is allowed to
    # finish that attempt. Only a fresh start (no existing progress
    # AND no assignment) is blocked.

    assignment = Assignment.query.filter_by(
        student_id=current_user.id,
        exam_id=id
    ).first()

    progress = get_progress(current_user.id, id)

    if assignment is None and progress is None:
        return "This examination has not been assigned to you."

    # ------------------------------------
    # Prevent duplicate attempt
    # ------------------------------------
    #
    # In normal operation a completed assignment no longer exists by
    # the time this runs -- save_attempt() deletes it automatically.
    # This check remains as a safety net.

    if assignment is not None and assignment.completed:
        return "You have already completed this examination."

    # ------------------------------------
    # Load all questions
    # ------------------------------------

    questions = Question.query.filter_by(
        exam_id=id
    ).all()

    if not questions:
        return "This examination has no questions."

    # ------------------------------------
    # Start or resume progress
    # ------------------------------------

    if progress is None:

        progress = create_progress(
            current_user.id,
            id,
            assignment.id if assignment is not None else None,
            questions,
            exam.duration_minutes,
        )

    # ------------------------------------
    # Load randomized order
    # ------------------------------------

    question_lookup = {
        q.id: q
        for q in questions
    }

    ordered_questions = []

    for question_id in progress.question_order:

        if question_id in question_lookup:

            ordered_questions.append(
                question_lookup[question_id]
            )

    questions = ordered_questions

    # ------------------------------------
    # Current question index
    # ------------------------------------

    index = progress.current_index

    # Safety check

    if index >= len(questions):
        index = len(questions) - 1
        progress.current_index = index
        db.session.commit()

    # ------------------------------------
    # Remaining time
    # ------------------------------------
    #
    # Recomputed from the absolute end_time stored in the database --
    # correct no matter how long the student was disconnected, since
    # nothing here depends on a client-side clock or session state.

    remaining = int(
        (progress.end_time - datetime.now()).total_seconds()
    )

    # ------------------------------------
    # Log exam start
    # ------------------------------------

    if index == 0:

        app_logger.info(
            f"EXAM START | "
            f"Student={current_user.student_id} | "
            f"Exam={exam.code} | "
            f"IP={request.remote_addr}"
        )

    # ------------------------------------
    # Handle Answer Submission
    # ------------------------------------

    if request.method == "POST":

        # Safety check
        if index >= len(questions):

            return redirect(
                url_for(
                    "exam_session.start_exam",
                    id=id
                )
            )

        current_question = questions[index]

        # Cross-check the question the browser thinks it is
        # answering against the question the server thinks is
        # current -- catches a stale tab, double submit, or desync.
        submitted_question_id = request.form.get(
            "question_id",
            type=int
        )

        if (
            submitted_question_id is not None
            and submitted_question_id != current_question.id
        ):
            return redirect(
                url_for(
                    "exam_session.start_exam",
                    id=id
                )
            )

        selected_answer = request.form.get("answer")

        # A question must be answered before moving on. Reject empty
        # submissions server-side and re-render the SAME question.
        if not selected_answer:

            flash(
                "Please select an answer before continuing."
            )

            return redirect(
                url_for(
                    "exam_session.start_exam",
                    id=id
                )
            )

        # Reassigning a NEW dict (rather than mutating progress.answers
        # in place) so SQLAlchemy reliably detects and persists the
        # change to this JSON column.
        answers = dict(progress.answers or {})
        answers[str(current_question.id)] = selected_answer
        progress.answers = answers

        db.session.commit()

        app_logger.info(
            f"ANSWER SAVED | "
            f"Student={current_user.student_id} | "
            f"Exam={exam.code} | "
            f"Question={current_question.id} | "
            f"Answer={selected_answer}"
        )

        # ------------------------------------
        # Move to next question
        # ------------------------------------

        if index < len(questions) - 1:

            progress.current_index = index + 1
            db.session.commit()

            return redirect(
                url_for(
                    "exam_session.start_exam",
                    id=id
                )
            )

        # ------------------------------------
        # Last Question Reached
        # Proceed to marking
        # ------------------------------------

        answers = progress.answers or {}

        score, total, percentage = score_exam(questions, answers)

        passed = save_attempt(
            exam, score, total, percentage, assignment
        )

        app_logger.info(
            f"EXAM COMPLETED | "
            f"Student={current_user.student_id} | "
            f"Exam={exam.code} | "
            f"Score={score}/{total} | "
            f"Percentage={percentage}% | "
            f"Passed={passed}"
        )

        clear_progress(progress)

        return render_template(

            "result.html",

            exam=exam,

            score=score,

            total=total,

            percentage=percentage,

            passed=passed
        )

    # ------------------------------------
    # Time Expired
    # ------------------------------------

    if remaining <= 0:

        app_logger.warning(
            f"EXAM TIMEOUT | "
            f"Student={current_user.student_id} | "
            f"Exam={exam.code}"
        )

        answers = progress.answers or {}

        score, total, percentage = score_exam(questions, answers)

        passed = save_attempt(
            exam, score, total, percentage, assignment
        )

        clear_progress(progress)

        flash(
            "Time is up. Your exam has been submitted automatically."
        )

        return render_template(

            "result.html",

            exam=exam,

            score=score,

            total=total,

            percentage=percentage,

            passed=passed

        )

    # ------------------------------------
    # Display Current Question
    # ------------------------------------

    question = questions[index]

    response = render_template(

        "take_exam.html",

        exam=exam,

        question=question,

        current=index + 1,

        total=len(questions),

        last=(index == len(questions) - 1),

        remaining=remaining

    )

    response = make_response(response)

    # ------------------------------------
    # Prevent browser caching
    # ------------------------------------

    response.headers["Cache-Control"] = (
        "no-store, no-cache, must-revalidate, "
        "max-age=0"
    )

    response.headers["Pragma"] = "no-cache"

    response.headers["Expires"] = "0"

    return response