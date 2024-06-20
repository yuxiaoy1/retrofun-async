from flask import Flask

from app.blueprints.commands import commands
from app.blueprints.main import main
from app.config import Config
from app.extensions import create_async_session, db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    register_extensions(app)
    register_blueprints(app)

    return app


def register_blueprints(app: Flask):
    app.register_blueprint(commands)
    app.register_blueprint(main)


def register_extensions(app: Flask):
    db.init_app(app)
    with app.app_context():
        db.Session = create_async_session(db.engine.url)
    # or configure as below
    # db.Session = create_session(app.config.get("SQLALCHEMY_DATABASE_URI"))
