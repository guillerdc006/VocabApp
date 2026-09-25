import json

from app.extensions import db
from app.models import SessionHistory, WordStats


class TestMatcherRuta:
    def test_renders_dos_columnas(self, client, make_word):
        make_word("apple", "manzana")
        make_word("dog", "perro")
        make_word("house", "casa")
        body = client.get("/study/match").data.decode()
        assert "Matcher de vocabulario" in body
        assert "Espanol" in body
        assert "Ingles" in body
        assert body.count("list-group-item-action") == 6
        assert "manzana" in body and "apple" in body

    def test_limite_10_parejas(self, client, make_word):
        for i in range(12):
            make_word(f"word{i}", f"palabra{i}")
        body = client.get("/study/match").data.decode()
        assert body.count("list-group-item-action") == 20

    def test_sin_palabras(self, client):
        body = client.get("/study/match").data.decode()
        assert "Aun no hay palabras" in body
        assert body.count("list-group-item-action") == 0


class TestMatcherCompleto:
    def test_registra_sesiones_tipo_match_sin_tocar_sm2(self, app, client, make_word):
        w1 = make_word("apple", "manzana")
        w2 = make_word("dog", "perro")
        resp = client.post(
            "/study/match/complete",
            data={"ids": json.dumps({"ids": [w1, w2]})},
        )
        assert resp.status_code == 302
        with app.app_context():
            rows = (
                db.session.query(SessionHistory)
                .filter(SessionHistory.session_type == "match")
                .all()
            )
            assert len(rows) == 2
            assert all(r.is_correct and r.validator_source == "match" for r in rows)
            assert all(r.direction == "match" for r in rows)
            for wid in (w1, w2):
                wstats = db.session.query(WordStats).filter_by(word_id=wid).first()
                assert wstats.times_practiced == 0
                assert wstats.next_review is None

    def test_con_ids_vacios_no_registra(self, app, client, make_word):
        make_word("apple", "manzana")
        resp = client.post("/study/match/complete", data={"ids": json.dumps({"ids": []})})
        assert resp.status_code == 302
        with app.app_context():
            assert db.session.query(SessionHistory).count() == 0