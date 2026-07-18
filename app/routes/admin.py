from flask import (Blueprint, render_template, abort)
from flask_login import (login_required, current_user)
from app.logger import app_logger


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