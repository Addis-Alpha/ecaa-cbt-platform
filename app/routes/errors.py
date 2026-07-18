from flask import (
    Blueprint,
    render_template,
)

from app.extensions import db
from app.logger import error_logger


errors_bp = Blueprint(
    "errors",
    __name__,
)


# ==========================
# 404 - NOT FOUND
# ==========================

@errors_bp.app_errorhandler(404)
def not_found_error(e):

    return render_template(
        "errors/404.html"
    ), 404


# ==========================
# 403 - FORBIDDEN
# ==========================

@errors_bp.app_errorhandler(403)
def forbidden_error(e):

    return render_template(
        "errors/403.html"
    ), 403


# ==========================
# 500 - INTERNAL SERVER ERROR
# ==========================

@errors_bp.app_errorhandler(500)
def internal_server_error(e):

    # IMPORTANT: roll back the DB session. If the error happened
    # mid-transaction (e.g. a failed commit, a constraint violation),
    # the SQLAlchemy session is left in a broken/aborted state. Without
    # this rollback, the NEXT request that reuses this session can
    # fail too, even if it has nothing to do with the original error.
    db.session.rollback()

    error_logger.error(
        f"INTERNAL SERVER ERROR | {e}",
        exc_info=True
    )

    return render_template(
        "errors/500.html"
    ), 500