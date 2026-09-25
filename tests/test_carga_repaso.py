from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models import SessionHistory, Word, WordStats
from app.services.analytics import (
    daily_accuracy_by_type,
    review_skyline,
    daily_practice_rate,
)

NOW = datetime.now(timezone.utc)


def _add_history(app, word_id, is_correct, created, session_type="quiz"):
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
            direction="match" if session_type == "match" else "es_to_en",
            validator_source="match" if session_type == "match" else "spacy",
        )
    )
    db.session.commit()


class TestDailyAccuracyByType:
    def test_separa_por_tipo(self):
        today = NOW.date()
        rows = [
            (datetime(today.year, today.month, today.day, 10, tzinfo=timezone.utc), True, "quiz"),
            (datetime(today.year, today.month, today.day, 11, tzinfo=timezone.utc), False, "quiz"),
            (datetime(today.year, today.month, today.day, 12, tzinfo=timezone.utc), True, "match"),
        ]
        result = daily_accuracy_by_type(rows)
        assert set(result) == {"quiz", "match"}
        assert all(len(result[t]) == 30 for t in result)
        assert result["quiz"][-1]["accuracy"] == 50
        assert result["quiz"][-1]["total"] == 2
        assert result["match"][-1]["accuracy"] == 100
        assert result["match"][-1]["total"] == 1

    def test_tipo_sin_actividad_todo_none(self):
        today = NOW.date()
        rows = [
            (datetime(today.year, today.month, today.day, 10, tzinfo=timezone.utc), True, "match"),
        ]
        result = daily_accuracy_by_type(rows)
        assert result["quiz"][-1]["accuracy"] is None
        assert result["match"][-1]["accuracy"] == 100


class TestReviewSkyline:
    def test_ventana_14_dias_desde_manana(self):
        today = NOW.date()
        rows = [
            today,                      # hoy -> excluido
            today + timedelta(days=1),  # manana -> incluido
            today + timedelta(days=14), # ultimo dia -> incluido
            today + timedelta(days=15), # fuera -> excluido
        ]
        skyline = review_skyline(rows)
        assert len(skyline) == 14
        assert skyline[0]["count"] == 1
        assert skyline[13]["count"] == 1
        assert skyline[1]["count"] == 0
        assert sum(d["count"] for d in skyline) == 2


class TestDailyPracticeRate:
    def test_palabras_distintas_por_dia(self):
        today = NOW.date()
        yesterday = today - timedelta(days=1)
        rows = [
            (NOW, 1),
            (NOW, 1),
            (NOW, 2),
            (datetime(yesterday.year, yesterday.month, yesterday.day, 9, tzinfo=timezone.utc), 3),
        ]
        rate = daily_practice_rate(rows, days=7)
        assert len(rate) == 7
        assert rate[-1]["count"] == 2
        assert rate[-2]["count"] == 1
        assert rate[0]["count"] == 0


class TestCargaEnPaginas:
    def test_stats_muestra_panel_y_graficos(self, app, client, make_word):
        word_id = make_word("apple", "manzana", practiced=1, correct=1)
        make_word("dog", "perro")
        body = client.get("/study/stats").data.decode()
        assert "Carga de repaso (SM-2)" in body
        assert "reviewChart" in body
        assert "rateChart" in body
        assert "Cola total" in body
        assert "Nuevas" in body
        assert "Vencidas" in body

    def test_evolucion_incluye_solo_tipos_activos(self, app, client, make_word):
        word_id = make_word("apple", "manzana")
        with app.app_context():
            _add_history(app, word_id, True, NOW, session_type="quiz")
        evolution = self._load_evolution(client)
        assert any(d["total"] > 0 for d in evolution["quiz"])
        assert all(d["total"] == 0 for d in evolution["match"])

        with app.app_context():
            _add_history(app, word_id, True, NOW, session_type="match")
        evolution = self._load_evolution(client)
        assert any(d["total"] > 0 for d in evolution["match"])

    @staticmethod
    def _load_evolution(client):
        import json
        import re

        body = client.get("/study/stats").data.decode()
        match = re.search(r"const evolution = (.+?);", body)
        assert match, "no se encontro el payload de evolucion"
        return json.loads(match.group(1))

    def test_dashboard_muestra_tarjeta_carga(self, app, client, make_word):
        make_word("apple", "manzana")
        body = client.get("/").data.decode()
        assert "Carga de repaso:" in body
        assert "nuevas" in body
        assert "vencidas" in body
        assert "en cola" in body