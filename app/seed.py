from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.user import User
from app.logger import app_logger, security_logger


# Change these if you want a different default -- they're only used
# the very first time the app starts against a database with no
# admin account in it at all.
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"


def seed_default_admin():
    """
    Ensures at least one admin account exists. Safe to call on every
    startup: it only actually creates anything the FIRST time it runs
    against a database that has zero admin accounts -- i.e. a brand
    new deployment, or a freshly created/empty database. On every
    subsequent startup (once any admin exists), this is a no-op.

    Why this matters: without it, a fresh deployment has no way to
    log in at all -- there's no signup page, and the database starts
    completely empty.

    The created account:
      - username "admin", password "admin123" -- a FIXED, publicly
        documented default. This is intentionally not secret; it's
        meant to be changed immediately.
      - must_change_password=True -- the app will not let this
        account do anything except change its password until that
        happens (enforced in app/__init__.py's before_request hook).
      - is_super_admin=True -- otherwise a fresh deployment would
        have no super admin, and therefore no way to ever create
        another admin account through the UI.
    """

    existing_admin = User.query.filter_by(
        role="admin"
    ).first()

    if existing_admin:
        return

    default_admin = User(
        username=DEFAULT_ADMIN_USERNAME,
        student_id=None,
        full_name="System Administrator",
        password=generate_password_hash(DEFAULT_ADMIN_PASSWORD),
        role="admin",
        is_super_admin=True,
        must_change_password=True,
    )

    db.session.add(default_admin)
    db.session.commit()

    security_logger.warning(
        "DEFAULT ADMIN CREATED | "
        f"Username={DEFAULT_ADMIN_USERNAME} | "
        "Using the fixed default password -- MUST be changed on "
        "first login."
    )

    app_logger.info(
        "No admin account found on startup. Created default admin "
        f"'{DEFAULT_ADMIN_USERNAME}' with a temporary password "
        f"('{DEFAULT_ADMIN_PASSWORD}'). Sign in and change the "
        "password immediately -- the app will not let this account "
        "do anything else until that's done."
    )