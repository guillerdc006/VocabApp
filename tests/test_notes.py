from app import create_app
from app.models import Word, WordStats


def test_palabra_con_notes(client, make_word):
    word_id = make_word("apple", "manzana", notes="fruta roja")
    with client.application.app_context():
        word = Word.query.filter_by(english="apple").first()
        assert word.notes == "fruta roja"
        assert word.stats is not None


def test_notes_opcional_es_none(client, make_word):
    word_id = make_word("dog", "perro")
    with client.application.app_context():
        word = Word.query.filter_by(english="dog").first()
        assert word.notes is None


def test_edit_schema_create_all_incluye_notes(app):
    with app.app_context():
        from app.extensions import db

        cols = {c.name for c in Word.__table__.columns}
        assert "notes" in cols
        assert WordStats.query.count() == 0