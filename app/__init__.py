import os
from flask import Flask
from .config import Config
from .extensions import db, migrate


def create_app(config_class=None):
    app = Flask(__name__, instance_relative_config=True)

    if config_class is None:
        config_class = Config
    app.config.from_object(config_class)

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)

    from .routes.main import main_bp
    from .routes.vocabulary import vocab_bp
    from .routes.study import study_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(vocab_bp, url_prefix="/vocabulary")
    app.register_blueprint(study_bp, url_prefix="/study")

    with app.app_context():
        from . import models
        db.create_all()

    return app
