class TestHint:
    def test_muestra_boton_pista_con_notes(self, client, make_word):
        make_word("abroad", "en el extranjero", notes="se usa con to go")
        resp = client.get("/study/quiz")
        body = resp.data.decode()
        assert 'id="hintBtn"' in body
        assert "se usa con to go" in body
        assert "d-none" in body

    def test_sin_notes_si_hay_boton_con_texto_default(self, client, make_word):
        make_word("apple", "manzana")
        resp = client.get("/study/quiz")
        body = resp.data.decode()
        assert 'id="hintBtn"' in body
        assert "La palabra no tiene observacion." in body