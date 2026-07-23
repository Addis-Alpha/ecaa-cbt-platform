from flask import (Blueprint, render_template, abort, redirect, url_for, flash)
from flask_login import (login_required, current_user)
from app.extensions import db
from app.models.user import User
from app.logger import app_logger, security_logger


admin_bp = Blueprint(
    "admin",
    __name__,
)

# ==========================
# ADMIN DASHBOARD
# ==========================

@admin_bp.route("/dashboard")
@login_required
def dashboard():

    if current_user.role != "admin":
        abort(403)

    app_logger.info(
        f"ADMIN DASHBOARD | "
        f"Username={current_user.username}"
    )

    return render_template(
        "dashboard.html"
    )


# ==========================
# FORCE LOGOUT A STUCK USER
# ==========================
#
# NEW: clears a user's active_session_token, freeing up their login
# slot. Needed because a student's device can die, lose power, or
# lose network mid-exam without ever hitting the real /logout route
# -- without this, that student would be permanently blocked from
# logging back in (see auth.py:login). Any admin can use this, not
# just super admins, since it's an operational unblock rather than a
# sensitive account-management action.

@admin_bp.route("/force-logout/<int:user_id>", methods=["POST"])
@login_required
def force_logout(user_id):

    if current_user.role != "admin":
        abort(403)

    target_user = User.query.get_or_404(user_id)

    target_user.active_session_token = None
    db.session.commit()

    security_logger.warning(
        f"FORCE LOGOUT | "
        f"TargetUser={target_user.username or target_user.student_id} | "
        f"By={current_user.username} | "
    )

    flash(
        f"{target_user.full_name or target_user.username} has been "
        f"signed out and can log in again."
    )

    return redirect(
        url_for("admin.dashboard")
    )