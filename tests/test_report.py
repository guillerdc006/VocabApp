from datetime import datetime, timezone

from app.extensions import db
from app.models import SessionHistory


def _add_history(app, word_id, ok, at, session_type="quiz", direction="es_to_en"):
    with app.app_context():
        db.session.add(
            SessionHistory(
                word_id=word_id,
                english_answer="apple",
                sentence="I eat an apple every day.",
                is_correct=ok,
                sentence_valid=True,
                score=100,
                quality=5,
                created_at=at,
                session_type=session_type,
                direction=direction,
                validator_source="spacy",
            )
        )
        db.session.commit()


class TestInforme:
    def test_informe_con_datos(self, app, client, make_word):
        word_id = make_word("apple", "manzana", practiced=3, correct=2)
        now = datetime.now(timezone.utc)
        with app.app_context():
            for ok in (True, True, False):
                _add_history(app, word_id, ok, now)
        body = client.get("/report").data.decode()
        assert "Informe de progreso" in body
        assert "Descargar PDF" in body
        assert "data:image/png;base64," in body
        assert "apple" in body
        assert "manzana" in body
        assert "Cola total" in body
        assert "Precision quiz" in body

    def test_informe_incrusta_cinco_graficos(self, app, client, make_word):
        make_word("apple", "manzana")
        body = client.get("/report").data.decode()
        assert body.count("data:image/png;base64,") >= 5

    def test_informe_vacio_no_falla(self, client):
        resp = client.get("/report")
        assert resp.status_code == 200
        assert "Informe de progreso" in resp.data.decode()


class TestInformePdf:
    def test_pdf_se_descarga(self, app, client, make_word):
        word_id = make_word("apple", "manzana", practiced=3, correct=2)
        now = datetime.now(timezone.utc)
        with app.app_context():
            for ok in (True, True, False):
                _add_history(app, word_id, ok, now)
        resp = client.get("/report/pdf")
        assert resp.status_code == 200
        assert resp.mimetype == "application/pdf"
        assert resp.data[:4] == b"%PDF"
        assert "Content-Disposition" in resp.headers
        assert "informe-progreso" in resp.headers["Content-Disposition"]

    def test_pdf_vacio_no_falla(self, app, client):
        resp = client.get("/report/pdf")
        assert resp.status_code == 200
        assert resp.data[:4] == b"%PDF"
        assert len(resp.data) > 1000