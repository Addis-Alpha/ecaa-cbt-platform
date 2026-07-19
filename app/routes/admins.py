import io
import os
import subprocess
import tempfile
from datetime import datetime

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
    send_file,
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


# ==========================
# DATABASE BACKUP
# ==========================
#
# Shells out to pg_dump (bundled with any standard PostgreSQL
# install, including pgAdmin4's) using the same DB_* environment
# variables config.py already reads -- no separate connection config
# to keep in sync. Uses custom format (-Fc): compressed, and the
# standard format for pg_restore. The dump is captured entirely in
# memory rather than written to a temp file on disk, so there's
# nothing left behind to clean up -- fine for a database this size;
# for a very large database this would need rethinking (streaming to
# disk instead), but that's not a concern at this scale.

@admins_bp.route(
    "/admins/backup",
    methods=["GET"],
)
@login_required
def download_backup():

    require_super_admin()

    db_env = os.environ.copy()
    db_env["PGPASSWORD"] = os.getenv("DB_PASSWORD", "")

    command = [
        "pg_dump",
        "-h", os.getenv("DB_HOST", ""),
        "-p", os.getenv("DB_PORT", ""),
        "-U", os.getenv("DB_USER", ""),
        "-Fc",
        os.getenv("DB_NAME", ""),
    ]

    try:

        result = subprocess.run(
            command,
            env=db_env,
            capture_output=True,
            timeout=300,
        )

    except FileNotFoundError:

        flash(
            "pg_dump was not found. Make sure PostgreSQL's bin "
            "folder is on the system PATH where this app is running."
        )

        return redirect(
            url_for("admins.admins")
        )

    if result.returncode != 0:

        error_message = result.stderr.decode(errors="replace")

        security_logger.warning(
            f"DATABASE BACKUP FAILED | "
            f"By={current_user.username} | "
            f"Error={error_message[:500]}"
        )

        flash(
            "Backup failed. Check the application error log for "
            "details."
        )

        return redirect(
            url_for("admins.admins")
        )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ecaa_cbt_backup_{timestamp}.backup"

    buffer = io.BytesIO(result.stdout)
    buffer.seek(0)

    security_logger.warning(
        f"DATABASE BACKUP DOWNLOADED | "
        f"By={current_user.username}"
    )

    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/octet-stream",
    )


# ==========================
# DATABASE RESTORE
# ==========================
#
# DESTRUCTIVE. Completely replaces all current data with the contents
# of the uploaded backup file. Guarded by three layers: super-admin
# only, a typed "RESTORE" confirmation, and a JS confirm() dialog on
# the form itself (see admins.html). Uses pg_restore --clean
# --if-exists so the restore reliably overwrites existing objects
# rather than erroring out on "already exists" conflicts.
#
# IMPORTANT FOR THE ADMIN DOING THIS: restoring drops and recreates
# every table, including the user table -- this invalidates every
# active session app-wide, including the super admin's own. Restart
# the application afterward and expect to sign in again.

@admins_bp.route(
    "/admins/restore",
    methods=["POST"],
)
@login_required
def restore_backup():

    require_super_admin()

    confirmation = request.form.get(
        "confirm_text",
        ""
    ).strip()

    if confirmation != "RESTORE":

        flash(
            'You must type "RESTORE" exactly to confirm this action.'
        )

        return redirect(
            url_for("admins.admins")
        )

    uploaded_file = request.files.get("backup_file")

    if not uploaded_file or uploaded_file.filename == "":

        flash(
            "Please choose a backup file to restore."
        )

        return redirect(
            url_for("admins.admins")
        )

    file_bytes = uploaded_file.read()

    # Custom-format pg_dump files always start with this magic
    # signature -- checking it catches an obviously wrong file (e.g.
    # a plain .sql export, or an unrelated file) with a clear message
    # instead of a cryptic pg_restore failure.
    if not file_bytes.startswith(b"PGDMP"):

        flash(
            "This doesn't look like a valid PostgreSQL custom-format "
            "backup file. Use a file created by this page's "
            "\"Download Backup\" button."
        )

        return redirect(
            url_for("admins.admins")
        )

    db_env = os.environ.copy()
    db_env["PGPASSWORD"] = os.getenv("DB_PASSWORD", "")

    tmp_path = None

    try:

        fd, tmp_path = tempfile.mkstemp(suffix=".backup")

        with os.fdopen(fd, "wb") as tmp_file:
            tmp_file.write(file_bytes)

        command = [
            "pg_restore",
            "-h", os.getenv("DB_HOST", ""),
            "-p", os.getenv("DB_PORT", ""),
            "-U", os.getenv("DB_USER", ""),
            "-d", os.getenv("DB_NAME", ""),
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
            tmp_path,
        ]

        result = subprocess.run(
            command,
            env=db_env,
            capture_output=True,
            timeout=600,
        )

    except FileNotFoundError:

        flash(
            "pg_restore was not found. Make sure PostgreSQL's bin "
            "folder is on the system PATH where this app is running."
        )

        return redirect(
            url_for("admins.admins")
        )

    finally:

        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

    if result.returncode != 0:

        error_message = result.stderr.decode(errors="replace")

        security_logger.warning(
            f"DATABASE RESTORE FAILED OR HAD WARNINGS | "
            f"By={current_user.username} | "
            f"Error={error_message[:1000]}"
        )

        # pg_restore with --clean commonly reports a non-zero exit
        # even when the restore substantially succeeded (e.g.
        # "does not exist, skipping" for objects it tried to drop
        # that weren't there). Showing the actual output rather than
        # a flat "failed" message lets the admin judge for themselves
        # instead of assuming data loss when it may just be noise.
        flash(
            "pg_restore reported errors or warnings. This does NOT "
            "necessarily mean the restore failed -- check the "
            "application error log for the full output, then verify "
            "your data before assuming something is wrong."
        )

        return redirect(
            url_for("admins.admins")
        )

    security_logger.warning(
        f"DATABASE RESTORED FROM BACKUP | "
        f"By={current_user.username}"
    )

    flash(
        "Database restored successfully. Restart the application "
        "now -- everyone, including you, will need to sign in again."
    )

    return redirect(
        url_for("admins.admins")
    )