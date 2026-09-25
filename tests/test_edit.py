from app.extensions import db
from app.models import SessionHistory, Word, WordStats


class TestEdit:
    def test_get_edit_prefill(self, client, make_word):
        word_id = make_word("apple", "manzana", notes="fruta roja")
        resp = client.get(f"/vocabulary/edit/{word_id}")
        assert resp.status_code == 200
        body = resp.data.decode()
        assert 'name="english"' in body
        assert "apple" in body
        assert "fruta roja" in body

    def test_editar_actualiza_y_conserva_stats(self, client, make_word):
        word_id = make_word("apple", "manzana", practiced=4, correct=3)
        resp = client.post(
            f"/vocabulary/edit/{word_id}",
            data={
                "english": "apple red",
                "spanish": "manzana roja",
                "notes": "fruta de temporada",
            },
        )
        assert resp.status_code == 302

        with client.application.app_context():
            word = db.session.get(Word, word_id)
            assert word.english == "apple red"
            assert word.spanish == "manzana roja"
            assert word.notes == "fruta de temporada"
            assert word.stats.times_practiced == 4
            assert word.stats.times_correct == 3

    def test_editar_duplicado_rechazado(self, client, make_word):
        make_word("dog", "perro")
        word_id = make_word("apple", "manzana")
        resp = client.post(
            f"/vocabulary/edit/{word_id}",
            data={"english": "dog", "spanish": "otra", "notes": ""},
        )
        assert resp.status_code == 200

        with client.application.app_context():
            word = db.session.get(Word, word_id)
            assert word.english == "apple"
            assert word.spanish == "manzana"

    def test_editar_campos_vacios(self, client, make_word):
        word_id = make_word("apple", "manzana")
        resp = client.post(
            f"/vocabulary/edit/{word_id}",
            data={"english": " ", "spanish": "", "notes": ""},
        )
        assert resp.status_code == 200

        with client.application.app_context():
            word = db.session.get(Word, word_id)
            assert word.english == "apple"
            assert word.spanish == "manzana"


class TestAddConNotes:
    def test_agregar_con_notes(self, client):
        resp = client.post(
            "/vocabulary/add",
            data={
                "english": "apple",
                "spanish": "manzana",
                "notes": "fruta roja",
            },
        )
        assert resp.status_code == 302

        with client.application.app_context():
            word = Word.query.filter_by(english="apple").first()
            assert word.notes == "fruta roja"

    def test_historial_no_se_pierde_al_editar(self, client, make_word):
        word_id = make_word("many", "muchos")
        resp = client.post(
            "/study/quiz",
            data={
                "word_id": word_id,
                "english_answer": "many",
                "sentence": "I have many books.",
            },
        )
        assert resp.status_code == 302

        client.post(
            f"/vocabulary/edit/{word_id}",
            data={"english": "many many", "spanish": "muchisimos", "notes": ""},
        )

        with client.application.app_context():
            assert SessionHistory.query.filter_by(word_id=word_id).count() == 1
            assert WordStats.query.filter_by(word_id=word_id).first().times_practiced == 1