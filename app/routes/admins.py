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
from app.logger import app_logger, security_logger


admins_bp = Blueprint(
    "admins",
    __name__,
)


# ==========================
# ACCESS HELPER
# ==========================
#
# Only a super admin may reach any route in this file. A regular
# admin (is_super_admin == False) still has full access to exams,
# questions, examinees, assignments, and results -- those checks are
# all "role == admin" elsewhere and are untouched by this feature.
# This gate is specifically for managing OTHER admin accounts.

def require_super_admin():

    if current_user.role != "admin" or not current_user.is_super_admin:
        abort(403)


# ==========================
# MANAGE ADMINS
# ==========================

@admins_bp.route(
    "/admins",
    methods=["GET", "POST"],
)
@login_required
def admins():

    require_super_admin()

    if request.method == "POST":

        username = request.form.get(
            "username",
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

        grant_super_admin = request.form.get(
            "is_super_admin"
        ) == "on"

        existing = User.query.filter_by(
            username=username
        ).first()

        if existing:

            flash(
                "Username already exists."
            )

        else:

            admin = User(
                username=username,
                student_id=None,
                full_name=full_name,
                password=generate_password_hash(password),
                role="admin",
                is_super_admin=grant_super_admin,
            )

            db.session.add(admin)
            db.session.commit()

            security_logger.warning(
                f"ADMIN CREATED | "
                f"Username={admin.username} | "
                f"SuperAdmin={grant_super_admin} | "
                f"By={current_user.username}"
            )

            flash(
                "Admin added successfully."
            )

            return redirect(
                url_for(
                    "admins.admins"
                )
            )

    admin_list = User.query.filter_by(
        role="admin"
    ).order_by(
        User.full_name
    ).all()

    return render_template(
        "admins.html",
        admins=admin_list,
    )


# ==========================
# EDIT ADMIN
# ==========================

@admins_bp.route(
    "/admins/edit/<int:id>",
    methods=["GET", "POST"],
)
@login_required
def edit_admin(id):

    require_super_admin()

    admin = User.query.get_or_404(id)

    if admin.role != "admin":
        abort(403)

    if request.method == "POST":

        new_username = request.form.get(
            "username",
            ""
        ).strip()

        duplicate = User.query.filter(
            User.username == new_username,
            User.id != admin.id,
        ).first()

        if duplicate:

            flash(
                "Username already exists."
            )

            return redirect(
                url_for(
                    "admins.edit_admin",
                    id=id,
                )
            )

        grant_super_admin = request.form.get(
            "is_super_admin"
        ) == "on"

        # SAFEGUARD: if this admin is currently the last super admin
        # and the form is trying to demote them, block it -- without
        # this, the admin-management page could lock out everyone
        # permanently.
        if admin.is_super_admin and not grant_super_admin:

            remaining_super_admins = User.query.filter_by(
                role="admin",
                is_super_admin=True,
            ).count()

            if remaining_super_admins <= 1:

                flash(
                    "Cannot remove super admin privileges from the "
                    "last super admin. Promote another admin first."
                )

                return redirect(
                    url_for(
                        "admins.edit_admin",
                        id=id,
                    )
                )

        admin.username = new_username
        admin.full_name = request.form.get(
            "full_name",
            ""
        ).strip()

        admin.is_super_admin = grant_super_admin

        password = request.form.get(
            "password",
            ""
        )

        if password:

            admin.password = generate_password_hash(
                password
            )

        db.session.commit()

        security_logger.warning(
            f"ADMIN UPDATED | "
            f"Username={admin.username} | "
            f"SuperAdmin={admin.is_super_admin} | "
            f"By={current_user.username}"
        )

        flash(
            "Admin updated successfully."
        )

        return redirect(
            url_for(
                "admins.admins"
            )
        )

    return render_template(
        "edit_admin.html",
        admin=admin,
    )


# ==========================
# DELETE ADMIN
# ==========================

@admins_bp.route(
    "/admins/delete/<int:id>"
)
@login_required
def delete_admin(id):

    require_super_admin()

    admin = User.query.get_or_404(id)

    if admin.role != "admin":
        abort(403)

    # SAFEGUARD: never allow deleting your own account while signed
    # in as it -- avoids an accidental self-lockout mid-session.
    if admin.id == current_user.id:

        flash(
            "You cannot delete your own account while signed in."
        )

        return redirect(
            url_for(
                "admins.admins"
            )
        )

    # SAFEGUARD: never allow the LAST admin account (of any kind) to
    # be deleted.
    total_admins = User.query.filter_by(
        role="admin"
    ).count()

    if total_admins <= 1:

        flash(
            "Cannot delete the last remaining admin account."
        )

        return redirect(
            url_for(
                "admins.admins"
            )
        )

    # SAFEGUARD: never allow the LAST super admin to be deleted
    # either, even if other regular admins remain -- otherwise nobody
    # could reach this page again.
    if admin.is_super_admin:

        remaining_super_admins = User.query.filter_by(
            role="admin",
            is_super_admin=True,
        ).count()

        if remaining_super_admins <= 1:

            flash(
                "Cannot delete the last super admin. Promote "
                "another admin to super admin first."
            )

            return redirect(
                url_for(
                    "admins.admins"
                )
            )

    security_logger.warning(
        f"ADMIN DELETED | "
        f"Username={admin.username} | "
        f"By={current_user.username}"
    )

    db.session.delete(admin)
    db.session.commit()

    flash(
        "Admin deleted successfully."
    )

    return redirect(
        url_for(
            "admins.admins"
        )
    )