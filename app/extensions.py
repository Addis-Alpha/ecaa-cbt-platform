from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()

login_manager = LoginManager()

login_manager.login_view = "auth.login"


@login_manager.user_loader
def load_user(user_id):

    from app.models.user import User

    return db.session.get(User, int(user_id))