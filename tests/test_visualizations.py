from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models import SessionHistory
from app.services.analytics import daily_accuracy, activity_weeks


def _add_history(app, word_id, is_correct, created):
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
            session_type="quiz",
            direction="es_to_en",
            validator_source="spacy",
        )
    )
    db.session.commit()


class TestDailyAccuracy:
    def test_ventana_de_30_dias_con_dia_sin_actividad(self):
        today = datetime.now(timezone.utc).date()
        rows = [
            (datetime(today.year, today.month, today.day, 10, tzinfo=timezone.utc), True),
            (datetime(today.year, today.month, today.day, 11, tzinfo=timezone.utc), False),
            (datetime(today.year, today.month, today.day, 12, tzinfo=timezone.utc), True),
        ]
        result = daily_accuracy(rows)
        assert len(result) == 30
        assert result[-1]["accuracy"] == 67
        assert result[-1]["total"] == 3
        assert result[-2]["accuracy"] is None

    def test_ignora_fuera_de_ventana(self):
        today = datetime.now(timezone.utc).date()
        rows = [
            (datetime(today.year, today.month, today.day, 10, tzinfo=timezone.utc), True),
            (datetime.fromisoformat(f"{today - timedelta(days=60)}T10:00:00+00:00"), True),
        ]
        result = daily_accuracy(rows, window_days=30)
        assert sum(1 for d in result if d["total"]) == 1


class TestActivityWeeks:
    def test_cuadricula_y_niveles(self):
        today = datetime.now(timezone.utc).date()
        rows = [
            datetime(today.year, today.month, today.day, 10, tzinfo=timezone.utc),
            datetime(today.year, today.month, today.day, 12, tzinfo=timezone.utc),
            datetime(today.year, today.month, today.day, 13, tzinfo=timezone.utc),
            datetime(today.year, today.month, today.day, 14, tzinfo=timezone.utc),
            datetime(today.year, today.month, today.day, 15, tzinfo=timezone.utc),
        ]
        weeks = activity_weeks(rows, weeks=16)
        assert len(weeks) == 16
        assert all(len(w) == 7 for w in weeks)
        today_cell = weeks[-1][today.weekday()]
        assert today_cell["count"] == 5
        assert today_cell["level"] == 4
        assert not today_cell["future"]


class TestVisualizacionesEnStats:
    def test_seccion_y_canvas(self, app, client, make_word):
        word_id = make_word("apple", "manzana")
        now = datetime.now(timezone.utc)
        with app.app_context():
            _add_history(app, word_id, True, now)
            _add_history(app, word_id, False, now - timedelta(days=1))
        body = client.get("/study/stats").data.decode()
        assert "Evolucion de precision" in body
        assert "Calendario de actividad" in body
        assert "accuracyChart" in body
        assert "chart.umd.min.js" in body
        assert "16 semanas" in body