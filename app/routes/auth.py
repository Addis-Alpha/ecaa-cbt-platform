from flask import (Blueprint, render_template, request, redirect, url_for, flash, session)
from flask_login import (login_user, logout_user, login_required, current_user)
from werkzeug.security import (check_password_hash)

from app.models.user import User
from app.logger import app_logger, security_logger

auth = Blueprint("auth", __name__)

# ==========================
# LOGIN
# ==========================

@auth.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        identifier = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Try username first
        user = User.query.filter_by(
            username=identifier
        ).first()

        # If not found, try student ID
        if user is None:
            user = User.query.filter_by(
                student_id=identifier
            ).first()

        # Verify credentials
        if (
            user
            and
            check_password_hash(
                user.password,
                password
            )
        ):

            login_user(user)

            # NEW: reset the "completed this session" marker on every
            # fresh login. This is what makes a completed exam card
            # disappear from the student dashboard after they log out
            # and log back in -- the card's visibility is tied to this
            # list, and a new login always starts it empty. The score
            # itself is untouched; it lives permanently in Attempt and
            # still shows in Result History regardless of this list.
            session["completed_this_session"] = []

            if user.role == "admin":

                app_logger.info(
                    f"ADMIN LOGIN | "
                    f"Username={user.username} | "
                    f"IP={request.remote_addr}"
                )

                return redirect(
                    url_for(
                        "admin.dashboard"
                    )
                )

            elif user.role == "student":

                app_logger.info(
                    f"STUDENT LOGIN | "
                    f"StudentID={user.student_id} | "
                    f"IP={request.remote_addr}"
                )

                return redirect(
                    url_for(
                        "student.student_dashboard"
                    )
                )

            else:

                security_logger.warning(
                    f"UNKNOWN ROLE | "
                    f"User={user.username}"
                )

                flash("Account role is invalid.")
                return redirect(
                    url_for(
                        "auth.login"
                    )
                )

        # Login failed
        security_logger.warning(
            f"FAILED LOGIN | "
            f"Identifier={identifier} | "
            f"IP={request.remote_addr}"
        )

        flash("Invalid username or password.")

    return render_template(
        "login.html"
    )

# ==========================
# LOGOUT
# ==========================

@auth.route("/logout")
@login_required
def logout():

    app_logger.info(
        f"LOGOUT | "
        f"User={current_user.username} | "
        f"IP={request.remote_addr}"
    )

    logout_user()

    return redirect(
        url_for(
            "auth.login"
        )
    )