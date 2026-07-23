import uuid

from flask import (Blueprint, render_template, request, redirect, url_for, flash, session)
from flask_login import (login_user, logout_user, login_required, current_user)
from werkzeug.security import (check_password_hash, generate_password_hash)

from app.extensions import db
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

            # NEW: block this login if the account already has an
            # active session elsewhere. Admins can force-clear a
            # stuck token from the admin panel (see admin.py) if a
            # student's browser/device died mid-session without
            # logging out properly.
            if user.role == "student" and user.active_session_token is not None:

                security_logger.warning(
                    f"BLOCKED CONCURRENT LOGIN | "
                    f"User={user.username or user.student_id} | "
                    f"IP={request.remote_addr}"
                )

                flash(
                    "This account is already logged in on another "
                    "device. Please log out there first, or contact "
                    "an admin if you believe this is an error."
                )

                return redirect(
                    url_for("auth.login")
                )

            # NEW: issue a fresh random token for this login, store it
            # both on the User row (server-side source of truth) and
            # in this browser's session cookie. The before_request
            # hook compares the two on every request.
            new_token = str(uuid.uuid4())
            user.active_session_token = new_token
            db.session.commit()

            login_user(user)

            session["session_token"] = new_token

            # reset the "completed this session" marker on every
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

    # NEW: free up this user's session slot so they (or someone else,
    # if the account is shared) can log in again immediately.
    current_user.active_session_token = None
    db.session.commit()

    logout_user()

    return redirect(
        url_for(
            "auth.login"
        )
    )


# ==========================
# CHANGE PASSWORD
# ==========================
#
# Reachable by any signed-in user at any time to change their own
# password. Also the ONE page a must_change_password account is
# allowed to reach (see the before_request hook in app/__init__.py) --
# used to force the default admin off its fixed starting password.

@auth.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():

    if request.method == "POST":

        current_password = request.form.get(
            "current_password",
            ""
        )

        new_password = request.form.get(
            "new_password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if not check_password_hash(current_user.password, current_password):

            flash(
                "Current password is incorrect."
            )

            return redirect(
                url_for("auth.change_password")
            )

        if len(new_password) < 8:

            flash(
                "New password must be at least 8 characters long."
            )

            return redirect(
                url_for("auth.change_password")
            )

        if new_password != confirm_password:

            flash(
                "New password and confirmation do not match."
            )

            return redirect(
                url_for("auth.change_password")
            )

        if check_password_hash(current_user.password, new_password):

            flash(
                "New password must be different from your current "
                "password."
            )

            return redirect(
                url_for("auth.change_password")
            )

        current_user.password = generate_password_hash(new_password)
        current_user.must_change_password = False

        db.session.commit()

        security_logger.warning(
            f"PASSWORD CHANGED | "
            f"User={current_user.username or current_user.student_id} | "
            f"IP={request.remote_addr}"
        )

        flash(
            "Password changed successfully."
        )

        if current_user.role == "admin":

            return redirect(
                url_for("admin.dashboard")
            )

        else:

            return redirect(
                url_for("student.student_dashboard")
            )

    return render_template(
        "change_password.html"
    )