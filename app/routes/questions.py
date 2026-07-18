from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)

from flask_login import (
    login_required,
    current_user,
)

from app.extensions import db
from app.models.exam import Exam
from app.models.question import Question
from app.logger import app_logger


questions_bp = Blueprint(
    "questions",
    __name__,
)


# ==========================
# QUESTIONS
# ==========================

@questions_bp.route(
    "/exam/<int:id>/questions",
    methods=["GET", "POST"],
)
@login_required
def exam_questions(id):

    if current_user.role != "admin":
        return "Access denied", 403

    exam = Exam.query.get_or_404(id)

    if request.method == "POST":

        answer = request.form.get(
            "answer",
            ""
        ).strip().upper()

        if answer not in ["A", "B", "C", "D"]:

            flash(
                "Correct answer must be A, B, C or D."
            )

            return redirect(
                url_for(
                    "questions.exam_questions",
                    id=id,
                )
            )

        q = Question(
            exam_id=id,
            question_text=request.form.get(
                "question",
                ""
            ).strip(),
            option_a=request.form.get(
                "a",
                ""
            ).strip(),
            option_b=request.form.get(
                "b",
                ""
            ).strip(),
            option_c=request.form.get(
                "c",
                ""
            ).strip(),
            option_d=request.form.get(
                "d",
                ""
            ).strip(),
            correct_answer=answer,
            marks=int(
                request.form.get(
                    "marks"
                )
            ),
        )

        db.session.add(q)
        db.session.commit()

        app_logger.info(
            f"QUESTION CREATED | "
            f"Exam={exam.code} | "
            f"QuestionID={q.id} | "
            f"By={current_user.username}"
        )

        flash(
            "Question added successfully."
        )

        return redirect(
            url_for(
                "questions.exam_questions",
                id=id,
            )
        )

    questions = Question.query.filter_by(
        exam_id=id
    ).order_by(
        Question.id.asc()
    ).all()

    return render_template(
        "questions.html",
        exam=exam,
        questions=questions,
    )


# ==========================
# EDIT QUESTION
# ==========================

@questions_bp.route(
    "/question/edit/<int:id>",
    methods=["GET", "POST"],
)
@login_required
def edit_question(id):

    if current_user.role != "admin":
        return "Access denied", 403

    question = Question.query.get_or_404(id)

    if request.method == "POST":

        answer = request.form.get(
            "answer",
            ""
        ).strip().upper()

        if answer not in ["A", "B", "C", "D"]:

            flash(
                "Correct answer must be A, B, C or D."
            )

            return redirect(
                url_for(
                    "questions.edit_question",
                    id=id,
                )
            )

        question.question_text = request.form.get(
            "question",
            ""
        ).strip()

        question.option_a = request.form.get(
            "a",
            ""
        ).strip()

        question.option_b = request.form.get(
            "b",
            ""
        ).strip()

        question.option_c = request.form.get(
            "c",
            ""
        ).strip()

        question.option_d = request.form.get(
            "d",
            ""
        ).strip()

        question.correct_answer = answer

        question.marks = int(
            request.form.get(
                "marks"
            )
        )

        db.session.commit()

        app_logger.info(
            f"QUESTION UPDATED | "
            f"QuestionID={question.id} | "
            f"By={current_user.username}"
        )

        flash(
            "Question updated successfully."
        )

        return redirect(
            url_for(
                "questions.exam_questions",
                id=question.exam_id,
            )
        )

    return render_template(
        "edit_question.html",
        question=question,
    )


# ==========================
# DELETE QUESTION
# ==========================

@questions_bp.route(
    "/question/delete/<int:id>"
)
@login_required
def delete_question(id):

    if current_user.role != "admin":
        return "Access denied", 403

    question = Question.query.get_or_404(id)

    exam_id = question.exam_id

    app_logger.info(
        f"QUESTION DELETED | "
        f"QuestionID={question.id} | "
        f"By={current_user.username}"
    )

    db.session.delete(question)
    db.session.commit()

    flash(
        "Question deleted successfully."
    )

    return redirect(
        url_for(
            "questions.exam_questions",
            id=exam_id,
        )
    )