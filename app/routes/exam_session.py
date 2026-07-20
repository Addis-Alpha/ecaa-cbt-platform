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

from app.logger import app_logger

import random
import time


exam_session_bp = Blueprint(
    "exam_session",
    __name__,
)


# ======================================================
# Helper Functions
# ======================================================
#
# BUG FIX: Every session key that relates to a specific exam attempt
# must be namespaced by exam_id. Previously "answers" and
# "question_index" were global keys shared across ALL exams in the
# same browser session. That meant a student who had already made
# progress on one exam (or was assigned a second exam) could open a
# different exam and inherit the leftover question_index / answers
# from the first one -- silently skipping questions or submitting
# with mostly-unanswered questions. timer_key and order_key were
# already correctly namespaced; the fix below brings the other two
# in line with them.
# ======================================================

def get_timer_key(exam_id):
    """
    Returns the session key used for storing
    the end time of an exam.
    """
    return f"exam_end_time_{exam_id}"


def get_order_key(exam_id):
    """
    Returns the session key used for storing
    the randomized order of questions.
    """
    return f"question_order_{exam_id}"


def get_answers_key(exam_id):
    """
    Returns the session key used for storing
    the student's answers for THIS exam only.
    """
    return f"exam_answers_{exam_id}"


def get_index_key(exam_id):
    """
    Returns the session key used for storing
    the current question index for THIS exam only.
    """
    return f"exam_question_index_{exam_id}"


def initialize_exam_session(exam, questions):
    """
    Creates all required session variables
    the first time the student starts an exam.
    """

    timer_key = get_timer_key(exam.id)
    order_key = get_order_key(exam.id)
    answers_key = get_answers_key(exam.id)
    index_key = get_index_key(exam.id)

    # -----------------------------
    # Timer
    # -----------------------------
    if timer_key not in session:

        session[timer_key] = (
            int(time.time())
            +
            exam.duration_minutes * 60
        )

    # -----------------------------
    # Question order
    # -----------------------------
    if order_key not in session:

        ids = [q.id for q in questions]

        random.shuffle(ids)

        session[order_key] = ids

    # -----------------------------
    # Answers (per-exam)
    # -----------------------------
    if answers_key not in session:

        session[answers_key] = {}

    # -----------------------------
    # Current question (per-exam)
    # -----------------------------
    if index_key not in session:

        session[index_key] = 0

    session.modified = True


def clear_exam_session(exam_id):
    """
    Removes every session value
    related to one examination.
    """

    session.pop(get_answers_key(exam_id), None)
    session.pop(get_index_key(exam_id), None)

    session.pop(
        get_timer_key(exam_id),
        None
    )

    session.pop(
        get_order_key(exam_id),
        None
    )

    session.modified = True


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

    # NEW: record that THIS ATTEMPT belongs to the current login
    # session. The dashboard only shows a "Completed" card for
    # attempts in this list; it's reset to empty on every fresh login
    # (see auth.py), which is what makes the card disappear next time
    # the student signs in. We track by attempt.id rather than
    # assignment.id now, because the assignment row is about to be
    # deleted below -- the attempt is what survives permanently.
    completed_ids = session.get("completed_this_session", [])

    if attempt.id not in completed_ids:
        completed_ids.append(attempt.id)

    session["completed_this_session"] = completed_ids
    session.modified = True

    # NEW: auto-remove the assignment now that it's been fulfilled.
    # Previously the admin had to manually delete a completed
    # assignment before they could reassign the same exam to the same
    # student -- the duplicate check in assign_exam() would otherwise
    # block it. The score is safe: it's already saved above in
    # Attempt, and the assignment_id FK uses ON DELETE SET NULL, so
    # this deletion can't cascade into losing the score record.
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
    # Verify assignment
    # ------------------------------------
    #
    # An admin can remove an assignment at any time, including while
    # the student is mid-exam. Per product decision: a student who is
    # already mid-exam (i.e. has a live session for this exam_id) is
    # allowed to finish that attempt. Only a fresh start (no existing
    # session AND no assignment) is blocked. The attempt itself doesn't
    # depend on the Assignment row -- Attempt is keyed by
    # student_id/exam_id, not assignment_id -- so this is safe.

    assignment = Assignment.query.filter_by(
        student_id=current_user.id,
        exam_id=id
    ).first()

    has_active_session = get_order_key(id) in session

    if assignment is None and not has_active_session:
        return "Either You have compeleted the Exam or " \
        "This examination has not been assigned to you. " \
        "Contact the Exam administrator if you think this is a mistake."

    # ------------------------------------
    # Prevent duplicate attempt
    # ------------------------------------
    #
    # In normal operation a completed assignment no longer exists by
    # the time this runs -- save_attempt() deletes it automatically.
    # This check remains as a safety net (e.g. a completed assignment
    # that predates this behavior, or a rare race between two
    # concurrent submissions before the delete commits).

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
    # Initialize session
    # ------------------------------------

    initialize_exam_session(
        exam,
        questions
    )

    timer_key = get_timer_key(exam.id)
    order_key = get_order_key(exam.id)
    answers_key = get_answers_key(exam.id)
    index_key = get_index_key(exam.id)

    # ------------------------------------
    # Load randomized order
    # ------------------------------------

    question_lookup = {
        q.id: q
        for q in questions
    }

    ordered_questions = []

    for question_id in session[order_key]:

        if question_id in question_lookup:

            ordered_questions.append(
                question_lookup[question_id]
            )

    questions = ordered_questions

    # ------------------------------------
    # Current question index
    # ------------------------------------

    index = session[index_key]

    # Safety check

    if index >= len(questions):
        index = len(questions) - 1
        session[index_key] = index

    # ------------------------------------
    # Remaining time
    # ------------------------------------

    remaining = (
        session[timer_key]
        -
        int(time.time())
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

        # BUG FIX: cross-check the question the browser thinks it is
        # answering against the question the server thinks is current.
        # If they disagree (stale tab, double submit, session desync),
        # re-render the current question instead of silently recording
        # the answer against the wrong question.
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

        # REQUIREMENT: a question must be answered before the student
        # can move on. Reject empty submissions here (server-side, so
        # it can't be bypassed by disabling JS / editing the form) and
        # re-render the SAME question instead of advancing.
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

        # BUG FIX: previously an answer, once saved, could never be
        # changed -- a student could correct a mis-click right up
        # until they clicked Next/Submit. Every valid submission
        # simply overwrites the stored answer for the current question.
        answers = session.get(answers_key, {})

        answers[str(current_question.id)] = selected_answer

        session[answers_key] = answers
        session.modified = True

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

            session[index_key] = index + 1

            session.modified = True

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

        answers = session.get(answers_key, {})

        score, total, percentage = score_exam(questions, answers)

        passed = save_attempt(
            exam, score, total, percentage, assignment
        )

        # ------------------------------------
        # Professional Logging
        # ------------------------------------

        app_logger.info(
            f"EXAM COMPLETED | "
            f"Student={current_user.student_id} | "
            f"Exam={exam.code} | "
            f"Score={score}/{total} | "
            f"Percentage={percentage}% | "
            f"Passed={passed}"
        )

        # ------------------------------------
        # Clean Session
        # ------------------------------------

        clear_exam_session(
            exam.id
        )

        # ------------------------------------
        # Show Result
        # ------------------------------------

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

        answers = session.get(answers_key, {})

        score, total, percentage = score_exam(questions, answers)

        passed = save_attempt(
            exam, score, total, percentage, assignment
        )

        clear_exam_session(
            exam.id
        )

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