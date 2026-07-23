from datetime import datetime, timedelta

from flask import Flask, request, redirect, url_for, session

from flask_login import current_user

from config import Config

from app.extensions import (
    db,
    login_manager,
)

from app.logger import app_logger


# NEW: how long a session can sit with no page requests before it's
# automatically treated as abandoned and freed up. 20 minutes per
# product decision -- covers a closed tab, dead device, or dropped
# wifi without needing an admin to manually notice and intervene.
INACTIVITY_TIMEOUT = timedelta(minutes=20)


def create_app():

    # -------------------------
    # Create Flask application
    # -------------------------

    app = Flask(__name__)

    # -------------------------
    # Configuration
    # -------------------------

    app.config.from_object(Config)

    # -------------------------
    # Initialize extensions
    # -------------------------

    db.init_app(app)
    login_manager.init_app(app)

    login_manager.login_view = "auth.login"

    app_logger.info(
        "========== ECAA CBT Server Started =========="
    )

    # -------------------------
    # Import database models
    # -------------------------

    from app.models.user import User
    from app.models.exam import Exam
    from app.models.question import Question
    from app.models.assignment import Assignment
    from app.models.attempt import Attempt
    from app.models.exam_progress import ExamProgress
    from app.models.system_heartbeat import SystemHeartbeat

    with app.app_context():

        db.create_all()

        from app.seed import seed_default_admin
        seed_default_admin()

        from app.heartbeat import (
            apply_downtime_compensation,
            start_heartbeat_thread,
        )
        apply_downtime_compensation()

    start_heartbeat_thread(app)

    # -------------------------
    # Import blueprints
    # -------------------------

    from app.routes.auth import auth
    from app.routes.admin import admin_bp
    from app.routes.student import student_bp
    from app.routes.students import students_bp
    from app.routes.exams import exams_bp
    from app.routes.questions import questions_bp
    from app.routes.assignments import assignments_bp
    from app.routes.results import results_bp
    from app.routes.exam_session import exam_session_bp
    from app.routes.errors import errors_bp
    from app.routes.admins import admins_bp

    # -------------------------
    # Register blueprints
    # -------------------------

    app.register_blueprint(auth)
    app.register_blueprint(admin_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(exams_bp)
    app.register_blueprint(questions_bp)
    app.register_blueprint(assignments_bp)
    app.register_blueprint(results_bp)
    app.register_blueprint(exam_session_bp)
    app.register_blueprint(errors_bp)
    app.register_blueprint(admins_bp)

    # -------------------------
    # Force password change when required
    # -------------------------

    @app.before_request
    def enforce_password_change():

        if not current_user.is_authenticated:
            return

        if not getattr(current_user, "must_change_password", False):
            return

        if request.endpoint is None:
            return

        allowed_endpoints = {
            "auth.change_password",
            "auth.logout",
            "static",
        }

        if request.endpoint in allowed_endpoints:
            return

        return redirect(
            url_for("auth.change_password")
        )

    # -------------------------
    # Enforce single active session per user + inactivity timeout
    # -------------------------
    #
    # Every login issues a fresh random token, stored both on the
    # User row (server-side truth) and in this browser's session
    # cookie (see auth.py:login). On every request:
    #
    #   1. If this user has no active session on record at all,
    #      nothing to check -- let them through (covers admins
    #      exempt from the single-session block, and any other
    #      edge case).
    #   2. If they've been inactive for longer than
    #      INACTIVITY_TIMEOUT, treat the session as abandoned: clear
    #      the token server-side and force this browser to log out.
    #      Covers a closed tab / dead device / dropped connection
    #      that never hit the real /logout route.
    #   3. If the browser's token doesn't match the server's record
    #      at all (e.g. an admin used Force Logout, or the account
    #      was somehow logged in twice), force this browser to log
    #      out too.
    #   4. Otherwise, this is a normal, current request -- stamp
    #      last_activity as now.

    @app.before_request
    def enforce_single_session():

        if not current_user.is_authenticated:
            return

        if request.endpoint is None:
            return

        allowed_endpoints = {
            "auth.logout",
            "static",
        }

        if request.endpoint in allowed_endpoints:
            return

        token_on_record = getattr(current_user, "active_session_token", None)

        if token_on_record is None:
            return

        last_activity = getattr(current_user, "last_activity", None)

        if last_activity is not None:

            if datetime.utcnow() - last_activity > INACTIVITY_TIMEOUT:

                from flask_login import logout_user
                from flask import flash

                current_user.active_session_token = None
                db.session.commit()

                logout_user()
                session.clear()

                flash(
                    "You were logged out due to 20 minutes of "
                    "inactivity. Please log in again."
                )

                return redirect(
                    url_for("auth.login")
                )

        token_in_browser = session.get("session_token")

        if token_in_browser != token_on_record:

            from flask_login import logout_user
            from flask import flash

            logout_user()
            session.clear()

            flash(
                "Your session has ended because this account was "
                "logged in elsewhere, or was signed out by an admin."
            )

            return redirect(
                url_for("auth.login")
            )

        current_user.last_activity = datetime.utcnow()
        db.session.commit()

    return app