from flask import Flask, request, redirect, url_for, session

from flask_login import current_user

from config import Config

from app.extensions import (
    db,
    login_manager,
)

from app.logger import app_logger


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

        # NEW: on a brand new/empty database, this creates a default
        # admin account so the app is never left with no way to log
        # in at all. No-op if any admin already exists (see
        # app/seed.py for details).
        from app.seed import seed_default_admin
        seed_default_admin()

        # NEW: detect a genuine server-side outage (the app itself
        # being down, not an individual student's own connection
        # dropping) and push every in-progress exam's deadline back
        # by exactly how long the server was unreachable. See
        # app/heartbeat.py for the full reasoning.
        from app.heartbeat import (
            apply_downtime_compensation,
            start_heartbeat_thread,
        )
        apply_downtime_compensation()

    # Runs outside the app_context block above since it manages its
    # own context internally (it's a long-lived background thread,
    # not a one-time startup task).
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
    #
    # While a user's must_change_password flag is True (set for
    # the auto-created default admin -- see app/seed.py), every page
    # except the change-password page itself, logout, and static
    # assets redirects back to the change-password page. This runs on
    # every request, so there's no way to route around it once signed
    # in with such an account.

    @app.before_request
    def enforce_password_change():

        if not current_user.is_authenticated:
            return

        if not getattr(current_user, "must_change_password", False):
            return

        # request.endpoint is None for URLs that don't match any
        # route at all (a genuine 404) -- let that fall through to
        # normal 404 handling instead of redirecting.
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
    # Enforce single active session per user
    # -------------------------
    #
    # NEW: every login issues a fresh random token, stored both on
    # the User row (server-side truth) and in this browser's session
    # cookie (see auth.py:login). On every request, we confirm the
    # two still match. If they don't -- e.g. an admin force-logged
    # this user out from another device, or the account somehow ended
    # up logged in twice -- this browser is immediately signed out.
    #
    # Runs after enforce_password_change on purpose: order between
    # the two before_request hooks doesn't matter functionally here,
    # since they check unrelated conditions, but keeping password
    # enforcement first preserves the original behavior/log ordering.

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

        token_in_browser = session.get("session_token")
        token_on_record = getattr(current_user, "active_session_token", None)

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

    return app