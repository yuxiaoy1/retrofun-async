import os

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite+aiosqlite:///" + os.path.join(basedir, "db.sqlite")
    )
