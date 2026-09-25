from app.models import SessionHistory


class TestReveal:
    def test_boton_revelar_siempre_visible_con_respuesta(self, client, make_word):
        make_word("apple", "manzana")
        body = client.get("/study/quiz").data.decode()
        assert 'id="revealBtn"' in body
        assert "No recuerdo / Ver respuesta" in body
        assert 'data-expected="apple"' in body

    def test_boton_revelar_direccion_inversa(self, client, make_word):
        make_word("apple", "manzana")
        body = client.get("/study/quiz?direction=en_to_es").data.decode()
        assert 'data-expected="manzana"' in body

    def test_revelar_marca_falla_aunque_respuesta_correcta(self, client, make_word):
        word_id = make_word("apple", "manzana")
        resp = client.post(
            "/study/quiz",
            data={
                "word_id": word_id,
                "english_answer": "apple",
                "sentence": "I eat an apple every day.",
                "revealed": "1",
            },
        )
        assert resp.status_code == 302
        with client.application.app_context():
            history = SessionHistory.query.filter_by(word_id=word_id).first()
            assert history.is_correct is False
            assert history.was_revealed is True
            assert history.sentence_valid is True
            assert history.quality == 3
            assert history.score == 50

    def test_revelar_no_otorga_puntos_por_palabra(self, client, make_word):
        word_id = make_word("apple", "manzana")
        client.post(
            "/study/quiz",
            data={
                "word_id": word_id,
                "english_answer": "apple",
                "sentence": "I eat an apple every day.",
                "revealed": "1",
            },
        )
        with client.application.app_context():
            history = SessionHistory.query.filter_by(word_id=word_id).first()
            assert history.is_correct is False
            assert history.was_revealed is True
            assert history.score == 50

    def test_sin_revelar_comportamiento_normal(self, client, make_word):
        word_id = make_word("apple", "manzana")
        client.post(
            "/study/quiz",
            data={
                "word_id": word_id,
                "english_answer": "apple",
                "sentence": "I eat an apple every day.",
            },
        )
        with client.application.app_context():
            history = SessionHistory.query.filter_by(word_id=word_id).first()
            assert history.is_correct is True
            assert history.was_revealed is False
            assert history.score == 100

    def test_resultado_muestra_aviso_de_ayuda(self, client, make_word):
        word_id = make_word("apple", "manzana")
        client.post(
            "/study/quiz",
            data={
                "word_id": word_id,
                "english_answer": "apple",
                "sentence": "I eat an apple every day.",
                "revealed": "1",
            },
        )
        history_id = None
        with client.application.app_context():
            history_id = SessionHistory.query.filter_by(word_id=word_id).first().id
        body = client.get(f"/study/result/{history_id}").data.decode()
        assert "Usaste ayuda" in body
        assert "respuesta fue revelada" in body

    def test_contador_de_ayuda_en_estadisticas(self, client, make_word):
        word_id = make_word("apple", "manzana")
        client.post(
            "/study/quiz",
            data={
                "word_id": word_id,
                "english_answer": "apple",
                "sentence": "I eat an apple every day.",
                "revealed": "1",
            },
        )
        word2 = make_word("many", "muchos")
        client.post(
            "/study/quiz",
            data={
                "word_id": word2,
                "english_answer": "many",
                "sentence": "I have many books.",
            },
        )
        body = client.get("/study/stats").data.decode()
        assert "Practicas con ayuda: 1" in body