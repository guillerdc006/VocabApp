import pytest

from app import create_app
from app.config import Config
from app.extensions import db


@pytest.fixture()
def app(tmp_path):
    db_path = tmp_path / "test.db"

    class TestConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + str(db_path)
        SECRET_KEY = "test-secret-key"

    application = create_app(TestConfig)

    with application.app_context():
        db.create_all()

    yield application

    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture(autouse=True)
def _ia_hermetico(monkeypatch):
    """Los tests nunca tocan la red: sin clave Gemini y proveedor spaCy por defecto."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("NLP_VALIDATOR", "spacy")


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def make_word(app):
    from datetime import datetime, timezone

    from app.models import Word, WordStats

    created = []

    def _make(english, spanish="traduccion", notes=None, practiced=0, correct=0):
        with app.app_context():
            word = Word(english=english, spanish=spanish, notes=notes)
            db.session.add(word)
            db.session.flush()
            stats = WordStats(word_id=word.id)
            if practiced:
                stats.times_practiced = practiced
                stats.times_correct = correct
                stats.level = 1
                stats.next_review = datetime.now(timezone.utc)
            db.session.add(stats)
            db.session.commit()
            created.append(word.id)
            return word.id

    yield _make

    with app.app_context():
        for wid in created:
            word = db.session.get(Word, wid)
            if word:
                db.session.delete(word)
        db.session.commit()