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

from werkzeug.security import (
    generate_password_hash,
)

from app.extensions import db
from app.models.user import User
from app.logger import app_logger


students_bp = Blueprint(
    "students",
    __name__,
)


# ==========================
# MANAGE STUDENTS
# ==========================

@students_bp.route(
    "/students",
    methods=["GET", "POST"],
)
@login_required
def students():

    if current_user.role != "admin":
        abort(403)

    if request.method == "POST":

        student_id = request.form.get(
            "student_id",
            ""
        ).strip()

        full_name = request.form.get(
            "full_name",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        # NEW: required fields, same as the others -- the model
        # itself doesn't enforce this at the DB level (nullable),
        # so it's checked here, consistent with how the rest of this
        # route already works.
        organization = request.form.get(
            "organization",
            ""
        ).strip()

        job_title = request.form.get(
            "job_title",
            ""
        ).strip()

        if not organization or not job_title:

            flash(
                "Organization and Job Title are required."
            )

            return redirect(
                url_for(
                    "students.students"
                )
            )

        existing = User.query.filter_by(
            student_id=student_id
        ).first()

        if existing:

            flash(
                "Student ID already exists."
            )

        else:

            student = User(
                username=None,
                student_id=student_id,
                full_name=full_name,
                password=generate_password_hash(password),
                role="student",
                organization=organization,
                job_title=job_title,
            )

            db.session.add(student)
            db.session.commit()

            app_logger.info(
                f"STUDENT CREATED | "
                f"StudentID={student.student_id} | "
                f"By={current_user.username}"
            )

            flash(
                "Student added successfully."
            )

            return redirect(
                url_for(
                    "students.students"
                )
            )

    # Search/filter examinees by ID or name.
    # GET /students?q=keyword -- case-insensitive, matches either
    # field. Empty/omitted "q" behaves exactly as before (full list).
    search = request.args.get(
        "q",
        ""
    ).strip()

    query = User.query.filter_by(
        role="student"
    )

    if search:

        like = f"%{search}%"

        query = query.filter(
            db.or_(
                User.student_id.ilike(like),
                User.full_name.ilike(like),
                User.organization.ilike(like),
                User.job_title.ilike(like),
            )
        )

    students = query.order_by(
        User.full_name
    ).all()

    return render_template(
        "students.html",
        students=students,
        search=search,
    )


# ==========================
# EDIT STUDENT
# ==========================

@students_bp.route(
    "/students/edit/<int:id>",
    methods=["GET", "POST"],
)
@login_required
def edit_student(id):

    if current_user.role != "admin":
        abort(403)

    student = User.query.get_or_404(id)

    if request.method == "POST":

        new_student_id = request.form.get(
            "student_id",
            ""
        ).strip()

        # NEW: required, same as create.
        organization = request.form.get(
            "organization",
            ""
        ).strip()

        job_title = request.form.get(
            "job_title",
            ""
        ).strip()

        if not organization or not job_title:

            flash(
                "Organization and Job Title are required."
            )

            return redirect(
                url_for(
                    "students.edit_student",
                    id=id,
                )
            )

        duplicate = User.query.filter(
            User.student_id == new_student_id,
            User.id != student.id,
        ).first()

        if duplicate:

            flash(
                "Student ID already exists."
            )

            return redirect(
                url_for(
                    "students.edit_student",
                    id=id,
                )
            )

        student.student_id = new_student_id
        student.full_name = request.form.get(
            "full_name",
            ""
        ).strip()

        student.organization = organization
        student.job_title = job_title

        password = request.form.get(
            "password",
            ""
        )

        if password:

            student.password = generate_password_hash(
                password
            )

        db.session.commit()

        app_logger.info(
            f"STUDENT UPDATED | "
            f"StudentID={student.student_id} | "
            f"By={current_user.username}"
        )

        flash(
            "Student updated successfully."
        )

        return redirect(
            url_for(
                "students.students"
            )
        )

    return render_template(
        "edit_student.html",
        student=student,
    )


# ==========================
# DELETE STUDENT
# ==========================

@students_bp.route(
    "/students/delete/<int:id>"
)
@login_required
def delete_student(id):

    if current_user.role != "admin":
        abort(403)

    student = User.query.get_or_404(id)

    if student.role != "student":
        abort(403)

    app_logger.info(
        f"STUDENT DELETED | "
        f"StudentID={student.student_id} | "
        f"By={current_user.username}"
    )

    db.session.delete(student)
    db.session.commit()

    flash(
        "Student deleted successfully."
    )

    return redirect(
        url_for(
            "students.students"
        )
    )