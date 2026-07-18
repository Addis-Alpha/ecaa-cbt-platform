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
from app.models.assignment import Assignment
from app.models.question import Question
from app.logger import app_logger


exams_bp = Blueprint(
    "exams",
    __name__,
)


# ==========================
# CREATE EXAM
# ==========================

@exams_bp.route(
    "/exams",
    methods=["GET", "POST"],
)
@login_required
def exams():

    if current_user.role != "admin":
        return "Access denied", 403

    if request.method == "POST":

        code = request.form.get(
            "code",
            ""
        ).strip()

        title = request.form.get(
            "title",
            ""
        ).strip()

        existing = Exam.query.filter_by(
            code=code
        ).first()

        if existing:

            flash(
                "Exam code already exists."
            )

        else:

            exam = Exam(
                code=code,
                title=title,
                duration_minutes=int(
                    request.form.get("duration")
                ),
                pass_mark=int(
                    request.form.get("pass_mark")
                ),
            )

            db.session.add(exam)
            db.session.commit()

            app_logger.info(
                f"EXAM CREATED | "
                f"Code={exam.code} | "
                f"By={current_user.username}"
            )

            flash(
                "Exam created successfully."
            )

            return redirect(
                url_for(
                    "exams.exams"
                )
            )

    exams = Exam.query.order_by(
        Exam.code.asc()
    ).all()

    return render_template(
        "exams.html",
        exams=exams,
    )


# ==========================
# EDIT EXAM
# ==========================

@exams_bp.route(
    "/exam/edit/<int:id>",
    methods=["GET", "POST"],
)
@login_required
def edit_exam(id):

    if current_user.role != "admin":
        return "Access denied", 403

    exam = Exam.query.get_or_404(id)

    if request.method == "POST":

        new_code = request.form.get(
            "code",
            ""
        ).strip()

        duplicate = Exam.query.filter(
            Exam.code == new_code,
            Exam.id != exam.id,
        ).first()

        if duplicate:

            flash(
                "Exam code already exists."
            )

            return redirect(
                url_for(
                    "exams.edit_exam",
                    id=id,
                )
            )

        exam.code = new_code
        exam.title = request.form.get(
            "title",
            ""
        ).strip()

        exam.duration_minutes = int(
            request.form.get("duration")
        )

        exam.pass_mark = int(
            request.form.get("pass_mark")
        )

        db.session.commit()

        app_logger.info(
            f"EXAM UPDATED | "
            f"Code={exam.code} | "
            f"By={current_user.username}"
        )

        flash(
            "Exam updated successfully."
        )

        return redirect(
            url_for(
                "exams.exams"
            )
        )

    return render_template(
        "edit_exam.html",
        exam=exam,
    )


# ==========================
# DELETE EXAM
# ==========================

@exams_bp.route(
    "/exam/delete/<int:id>"
)
@login_required
def delete_exam(id):

    if current_user.role != "admin":
        return "Access denied", 403

    exam = Exam.query.get_or_404(id)

    Assignment.query.filter_by(
        exam_id=id
    ).delete()

    Question.query.filter_by(
        exam_id=id
    ).delete()

    app_logger.info(
        f"EXAM DELETED | "
        f"Code={exam.code} | "
        f"By={current_user.username}"
    )

    db.session.delete(exam)
    db.session.commit()

    flash(
        "Exam deleted successfully."
    )

    return redirect(
        url_for(
            "exams.exams"
        )
    )