from app.extensions import db
from app.models import SessionHistory, WordStats

SENTENCE = "I like to eat an apple every day"


def _history_id(resp):
    return int(resp.headers["Location"].rstrip("/").split("/")[-1])


class TestDireccionInversaRender:
    def test_default_es_es_to_en(self, client, make_word):
        make_word("apple", "manzana")
        body = client.get("/study/quiz").data.decode()
        assert "Traduce al ingles" in body
        assert "Escribe la palabra en ingles" in body
        assert "quiz-word\">manzana" in body

    def test_selector_muestra_direccion_inversa(self, client, make_word):
        make_word("apple", "manzana")
        body = client.get("/study/quiz?direction=en_to_es").data.decode()
        assert "Traduce al espanol" in body
        assert "Escribe la traduccion en espanol" in body
        assert "quiz-word\">apple" in body
        assert "Traduce al ingles" not in body

    def test_direccion_persistida_en_sesion(self, client, make_word):
        make_word("apple", "manzana")
        client.get("/study/quiz?direction=en_to_es")
        body = client.get("/study/quiz").data.decode()
        assert "Traduce al espanol" in body

    def test_direccion_invalida_cae_a_default(self, client, make_word):
        make_word("apple", "manzana")
        body = client.get("/study/quiz?direction=xyz").data.decode()
        assert "Traduce al ingles" in body


class TestDireccionInversaPost:
    def test_post_inverso_correcto(self, app, client, make_word):
        wid = make_word("apple", "manzana")
        resp = client.post(
            "/study/quiz",
            data={
                "word_id": wid,
                "direction": "en_to_es",
                "english_answer": "manzana",
                "sentence": SENTENCE,
            },
        )
        assert resp.status_code == 302
        with app.app_context():
            h = db.session.get(SessionHistory, _history_id(resp))
            assert h.direction == "en_to_es"
            assert h.is_correct
            assert h.english_answer == "manzana"
            ws = db.session.query(WordStats).filter_by(word_id=wid).first()
            assert ws.times_practiced == 1
            assert ws.times_correct == 1

    def test_post_inverso_incorrecto(self, app, client, make_word):
        wid = make_word("apple", "manzana")
        resp = client.post(
            "/study/quiz",
            data={
                "word_id": wid,
                "direction": "en_to_es",
                "english_answer": "pera",
                "sentence": SENTENCE,
            },
        )
        with app.app_context():
            h = db.session.get(SessionHistory, _history_id(resp))
            assert h.direction == "en_to_es"
            assert not h.is_correct

    def test_resultado_muestra_direccion_inversa(self, client, make_word):
        wid = make_word("apple", "manzana")
        resp = client.post(
            "/study/quiz",
            data={
                "word_id": wid,
                "direction": "en_to_es",
                "english_answer": "manzana",
                "sentence": SENTENCE,
            },
        )
        body = client.get(resp.headers["Location"]).data.decode()
        assert "Palabra (ingles):" in body
        assert "manzana" in body