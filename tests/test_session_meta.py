from app.models import SessionHistory


class TestSessionMeta:
    def test_modelo_tiene_campos_nuevos(self, app):
        with app.app_context():
            cols = {c.name for c in SessionHistory.__table__.columns}
            assert {"session_type", "direction", "validator_source", "sentence_suggestion"} <= cols

    def test_quiz_registra_metadata(self, client, make_word):
        word_id = make_word("many", "muchos")
        client.post(
            "/study/quiz",
            data={
                "word_id": word_id,
                "english_answer": "many",
                "sentence": "I have many books.",
            },
        )
        with client.application.app_context():
            h = SessionHistory.query.first()
            assert h.session_type == "quiz"
            assert h.direction == "es_to_en"
            assert h.validator_source == "spacy"
            assert h.sentence_suggestion is None