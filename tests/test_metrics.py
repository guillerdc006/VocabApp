import re
from datetime import date, datetime, timedelta, timezone

from app.extensions import db
from app.models import SessionHistory
from app.services.analytics import compute_streaks, accuracy_by_dimension


def _add_history(app, word_id, is_correct, created, session_type="quiz", direction="es_to_en", validator_source="spacy"):
    db.session.add(
        SessionHistory(
            word_id=word_id,
            english_answer="answer",
            sentence="I like this word.",
            sentence_valid=True,
            is_correct=is_correct,
            score=100 if is_correct else 40,
            quality=5 if is_correct else 1,
            created_at=created,
            session_type=session_type,
            direction=direction,
            validator_source=validator_source,
        )
    )
    db.session.commit()


class TestComputeStreaks:
    def test_vacio(self):
        assert compute_streaks([]) == (0, 0)

    def test_sin_actividad_reciente(self):
        days = [date(2026, 1, 10)]
        assert compute_streaks(days) == (0, 1)

    def test_racha_actual_y_mejor(self):
        today = datetime.now(timezone.utc).date()
        current = [today - timedelta(days=i) for i in range(3)]
        past = [today - timedelta(days=i) for i in range(6, 11)]
        assert compute_streaks(current + past) == (3, 5)

    def test_racha_termina_ayer(self):
        today = datetime.now(timezone.utc).date()
        days = [today - timedelta(days=1), today - timedelta(days=2)]
        assert compute_streaks(days) == (2, 2)


class TestAccuracyByDimension:
    def test_agrupa_por_dimension(self):
        rows = [
            ("quiz", True),
            ("quiz", True),
            ("quiz", False),
            ("match", True),
        ]
        assert accuracy_by_dimension(rows) == {"quiz": 67, "match": 100}

    def test_vacio(self):
        assert accuracy_by_dimension([]) == {}


class TestMetricasEnStats:
    def test_metricas_visibles(self, app, client, make_word):
        word_id = make_word("apple", "manzana")
        now = datetime.now(timezone.utc)
        with app.app_context():
            for i in range(3):
                _add_history(app, word_id, True, now - timedelta(days=i))
            for i in range(6, 11):
                _add_history(app, word_id, True, now - timedelta(days=i))
        body = client.get("/study/stats").data.decode()
        assert "Racha actual" in body
        assert "Mejor racha" in body
        assert "Dias activos" in body
        assert 'fw-bold mt-2">3' in body
        assert 'fw-bold mt-2">5' in body
        assert 'fw-bold mt-2">8' in body

    def test_precision_por_tipo_y_direccion(self, app, client, make_word):
        word_id = make_word("apple", "manzana")
        now = datetime.now(timezone.utc)
        with app.app_context():
            for correct in (True, True, True, False):
                _add_history(app, word_id, correct, now, session_type="quiz")
            _add_history(app, word_id, True, now, session_type="match")
        body = client.get("/study/stats").data.decode()
        assert "75%" in body
        assert "100%" in body
        assert "80%" in body
        assert "Precision por tipo de sesion" in body
        assert "Precision por direccion" in body

    def test_precision_por_validador(self, app, client, make_word):
        word_id = make_word("apple", "manzana")
        now = datetime.now(timezone.utc)
        with app.app_context():
            for correct in (True, True, False):
                _add_history(app, word_id, correct, now, validator_source="gemini")
            for correct in (True, False):
                _add_history(app, word_id, correct, now, validator_source="spacy")
            _add_history(app, word_id, True, now, session_type="match", validator_source="match")
        body = client.get("/study/stats").data.decode()
        assert "Precision por validador" in body
        assert "IA (Gemini)" in body
        assert "Local (spaCy)" in body
        assert "67%" in body
        assert "50%" in body