from flask import Flask

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

    with app.app_context():
        db.create_all()

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

    return app