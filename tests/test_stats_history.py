from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models import SessionHistory


def _add_history(app, word_id, english_answer, is_correct, created, session_type="quiz"):
    db.session.add(
        SessionHistory(
            word_id=word_id,
            english_answer=english_answer,
            sentence="I like this word.",
            sentence_valid=True,
            is_correct=is_correct,
            score=100 if is_correct else 40,
            quality=5 if is_correct else 1,
            created_at=created,
            session_type=session_type,
            direction="es_to_en",
            validator_source="spacy",
        )
    )
    db.session.commit()


class TestHistorialCompleto:
    def test_paginacion_muestra_5_en_pagina_2(self, app, client, make_word):
        word_id = make_word("apple", "manzana")
        with app.app_context():
            for i in range(25):
                _add_history(
                    app, word_id, "apple", i % 2 == 0,
                    datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc) + timedelta(hours=i),
                )
        body1 = client.get("/study/stats").data.decode()
        body2 = client.get("/study/stats?page=2").data.decode()
        rows1 = body1.count("bi-check-circle-fill") + body1.count("bi-x-circle-fill")
        rows2 = body2.count("bi-check-circle-fill") + body2.count("bi-x-circle-fill")
        assert rows1 == 20
        assert rows2 == 5

    def test_filtro_por_palabra(self, app, client, make_word):
        apple_id = make_word("apple", "manzana")
        banana_id = make_word("banana", "platano")
        with app.app_context():
            _add_history(app, apple_id, "apple", True, datetime(2026, 9, 1, tzinfo=timezone.utc))
            _add_history(app, banana_id, "banana", True, datetime(2026, 9, 1, tzinfo=timezone.utc))
        body = client.get("/study/stats?word=banana").data.decode()
        assert "banana" in body
        assert body.count("apple") == 0

    def test_filtro_por_correctas(self, app, client, make_word):
        word_id = make_word("apple", "manzana")
        with app.app_context():
            for i in range(3):
                _add_history(app, word_id, "apple", True, datetime(2026, 9, 1, i, 0, tzinfo=timezone.utc))
            for i in range(2):
                _add_history(app, word_id, "apple", False, datetime(2026, 9, 2, i, 0, tzinfo=timezone.utc))
        body = client.get("/study/stats?correct=yes").data.decode()
        assert body.count("bi-check-circle-fill") == 3
        assert body.count("bi-x-circle-fill") == 0

    def test_filtro_por_fechas(self, app, client, make_word):
        word_id = make_word("apple", "manzana")
        with app.app_context():
            _add_history(app, word_id, "apple", True, datetime(2026, 8, 20, tzinfo=timezone.utc))
            _add_history(app, word_id, "apple", True, datetime(2026, 9, 5, tzinfo=timezone.utc))
        body = client.get("/study/stats?date_from=2026-09-01&date_to=2026-09-10").data.decode()
        assert body.count("apple") == 2
        assert "05/09" in body

    def test_filtro_por_tipo_sin_resultados(self, app, client, make_word):
        word_id = make_word("apple", "manzana")
        with app.app_context():
            _add_history(app, word_id, "apple", True, datetime(2026, 9, 1, tzinfo=timezone.utc), session_type="quiz")
        body = client.get("/study/stats?session_type=match").data.decode()
        assert "No hay sesiones con los filtros aplicados" in body