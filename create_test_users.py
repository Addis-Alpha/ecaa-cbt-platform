from app import create_app
from app.extensions import db
from app.models.user import User
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():

    admin = User.query.filter_by(username="admin").first()

    if not admin:
        admin = User(
            username = "admin",
            student_id = "A001",
            full_name = "System Admin",
            password = generate_password_hash("admin999"),
            role="admin"
        )

        db.session.add(admin)

    student = User.query.filter_by(student_id="S001").first()

    if not student:
        student = User(
            username=None,
            student_id="S001",
            full_name="Alpha Bravo Charlie",
            password=generate_password_hash("1234"),
            role="student"
        )

        db.session.add(student)
    db.session.commit()
print("Users created successfully")

