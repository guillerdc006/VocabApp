import io

from openpyxl import Workbook


class TestDashboard:
    def test_empty_dashboard_ok(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        body = resp.data.decode
        assert "Dashboard" in body()
        assert "0" in body()

    def test_dashboard_muestra_conteos(self, client, make_word):
        make_word("apple", "manzana")
        make_word("dog", "perro", practiced=3, correct=2)
        resp = client.get("/")
        body = resp.data.decode()
        assert "Palabras totales" in body
        assert "Palabras practicadas" in body
        assert "Pendientes para practica" in body


class TestQuiz:
    def test_quiz_vacio_redirige(self, client):
        resp = client.get("/study/quiz")
        assert resp.status_code == 302
        assert "/vocabulary/" in resp.headers["Location"]

    def test_quiz_muestra_palabra(self, client, make_word):
        make_word("many", "muchos")
        resp = client.get("/study/quiz")
        assert resp.status_code == 200
        body = resp.data.decode()
        assert 'name="word_id"' in body
        assert 'name="english_answer"' in body
        assert 'name="sentence"' in body

    def test_quiz_post_correcto_guarda_historial(self, client, make_word):
        word_id = make_word("many", "muchos")
        resp = client.post(
            "/study/quiz",
            data={
                "word_id": word_id,
                "english_answer": "many",
                "sentence": "I have many books.",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "/study/result/" in resp.headers["Location"]

        from app.models import SessionHistory

        with client.application.app_context():
            history = SessionHistory.query.filter_by(word_id=word_id).first()
            assert history is not None
            assert history.is_correct is True
            assert history.sentence_valid is True

    def test_quiz_post_incorrecto(self, client, make_word):
        word_id = make_word("many", "muchos")
        resp = client.post(
            "/study/quiz",
            data={
                "word_id": word_id,
                "english_answer": "wrong",
                "sentence": "I have many books.",
            },
        )
        assert resp.status_code == 302

        from app.models import SessionHistory

        with client.application.app_context():
            history = SessionHistory.query.filter_by(word_id=word_id).first()
            assert history.is_correct is False

    def test_resultado_muestra_acierto(self, client, make_word):
        word_id = make_word("many", "muchos")
        client.post(
            "/study/quiz",
            data={
                "word_id": word_id,
                "english_answer": "many",
                "sentence": "I have many books.",
            },
        )

        from app.models import SessionHistory

        history_id = None
        with client.application.app_context():
            history_id = SessionHistory.query.first().id

        resp = client.get(f"/study/result/{history_id}")
        assert resp.status_code == 200
        assert "Correcto" in resp.data.decode()

    def test_resultado_404(self, client):
        resp = client.get("/study/result/9999")
        assert resp.status_code == 404


class TestStats:
    def test_stats_vacio(self, client):
        resp = client.get("/study/stats")
        assert resp.status_code == 200
        assert "Estadisticas" in resp.data.decode()

    def test_stats_con_datos(self, client, make_word):
        make_word("hard1", "dificil1", practiced=5, correct=0)
        make_word("easy1", "facil1", practiced=5, correct=5)
        resp = client.get("/study/stats")
        body = resp.data.decode()
        assert "hard1" in body
        assert "easy1" in body


class TestVocabulary:
    def test_lista_vacia(self, client):
        resp = client.get("/vocabulary/")
        assert resp.status_code == 200
        assert "Vocabulario" in resp.data.decode()

    def test_lista_muestra_palabras(self, client, make_word):
        make_word("apple", "manzana")
        make_word("dog", "perro")
        resp = client.get("/vocabulary/")
        body = resp.data.decode()
        assert "apple" in body
        assert "dog" in body

    def test_busqueda(self, client, make_word):
        make_word("apple", "manzana")
        make_word("dog", "perro")
        resp = client.get("/vocabulary/?search=apple")
        body = resp.data.decode()
        assert "apple" in body
        assert "dog" not in body

    def test_paginacion(self, client, make_word):
        for i in range(25):
            make_word(f"word{i}", "traduccion")
        resp = client.get("/vocabulary/?page=2")
        assert resp.status_code == 200
        body = resp.data.decode()
        assert "word5" in body
        assert "word9" in body
        assert "word0" not in body

    def test_agregar_palabra(self, client):
        resp = client.post(
            "/vocabulary/add", data={"english": "apple", "spanish": "manzana"}
        )
        assert resp.status_code == 302

        from app.models import Word, WordStats

        with client.application.app_context():
            word = Word.query.filter_by(english="apple").first()
            assert word is not None
            assert word.stats is not None
            assert WordStats.query.filter_by(word_id=word.id).count() == 1

    def test_agregar_duplicada(self, client, make_word):
        make_word("apple", "manzana")
        resp = client.post(
            "/vocabulary/add", data={"english": "apple", "spanish": "manzana"}
        )
        assert resp.status_code == 302

        from app.models import Word

        with client.application.app_context():
            assert Word.query.filter_by(english="apple").count() == 1

    def test_agregar_sin_campos(self, client):
        resp = client.post("/vocabulary/add", data={"english": " ", "spanish": ""})
        assert resp.status_code == 302

        from app.models import Word

        with client.application.app_context():
            assert Word.query.count() == 0

    def test_eliminar_palabra(self, client, make_word):
        word_id = make_word("apple", "manzana")
        resp = client.post(f"/vocabulary/delete/{word_id}")
        assert resp.status_code == 302

        from app.extensions import db
        from app.models import Word

        with client.application.app_context():
            assert db.session.get(Word, word_id) is None


class TestImport:
    def test_import_sin_archivo(self, client):
        resp = client.post("/vocabulary/import")
        assert resp.status_code == 302

    def test_import_xlsx(self, client):
        wb = Workbook()
        ws = wb.active
        ws.append(["Inglés", "Español"])
        ws.append(["apple", "manzana"])
        ws.append(["dog", "perro"])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        resp = client.post(
            "/vocabulary/import",
            data={"file": (buf, "words.xlsx")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 302

        from app.models import Word

        with client.application.app_context():
            assert Word.query.filter_by(english="apple").first() is not None
            assert Word.query.filter_by(english="dog").first() is not None