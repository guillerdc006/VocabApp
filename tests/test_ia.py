from app.config import Config, get_api_key, get_gemini_timeout_ms, get_validator
from app.models import SessionHistory
from app.services import nlp_validator
from app.services.nlp_validator import (
    _parse_gemini_response,
    resolve_validator,
    validate_sentence_pipeline,
)


class TestConfigIA:
    def test_claves_ia_presentes(self):
        assert hasattr(Config, "GEMINI_API_KEY")
        assert hasattr(Config, "NLP_VALIDATOR")
        assert hasattr(Config, "GEMINI_TIMEOUT_MS")

    def test_validator_es_gemini_o_spacy(self):
        assert get_validator() in ("gemini", "spacy")

    def test_timeout_default(self, monkeypatch):
        monkeypatch.delenv("GEMINI_TIMEOUT_MS", raising=False)
        assert get_gemini_timeout_ms() == 3000

    def test_timeout_env_gana(self, monkeypatch):
        monkeypatch.setenv("GEMINI_TIMEOUT_MS", "1500")
        assert get_gemini_timeout_ms() == 1500

    def test_timeout_invalido_vuelve_al_default(self, monkeypatch):
        monkeypatch.setenv("GEMINI_TIMEOUT_MS", "abc")
        assert get_gemini_timeout_ms() == 3000

    def test_env_gana_sobre_el_default(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key-123")
        monkeypatch.setenv("NLP_VALIDATOR", "spacy")
        assert get_api_key() == "test-key-123"
        assert get_validator() == "spacy"

    def test_sin_env_usa_default_gemini(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("NLP_VALIDATOR", raising=False)
        assert get_validator() == "gemini"
        assert get_api_key() == ""

    def test_sin_clave_no_es_error(self):
        assert isinstance(get_api_key(), str)


class TestResolveValidator:
    def test_sin_clave_usar_spacy(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("NLP_VALIDATOR", "gemini")
        assert resolve_validator() == "spacy"

    def test_con_clave_y_gemini(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.setenv("NLP_VALIDATOR", "gemini")
        assert resolve_validator() == "gemini"

    def test_validator_spacy_ignora_clave(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.setenv("NLP_VALIDATOR", "spacy")
        assert resolve_validator() == "spacy"


class TestParseGeminiResponse:
    def test_respuesta_valida(self):
        text = '{"word_found": true, "has_verb": true, "token_count": 6, "details": "Correcta", "suggestion": null}'
        result = _parse_gemini_response(text)
        assert result["valid"] is True
        assert result["word_found"] is True
        assert result["has_verb"] is True
        assert result["token_count"] == 6
        assert result["suggestion"] is None

    def test_respuesta_invalida_con_sugerencia(self):
        text = (
            '{"word_found": false, "has_verb": true, "token_count": 5, '
            '"details": "Falta la palabra", "suggestion": "I like eating an apple."}'
        )
        result = _parse_gemini_response(text)
        assert result["valid"] is False
        assert result["word_found"] is False
        assert result["suggestion"] == "I like eating an apple."

    def test_ignora_cercos_markdown(self):
        text = '```json\n{"word_found": true, "has_verb": true, "token_count": 4, "details": "Correcta", "suggestion": null}\n```'
        assert _parse_gemini_response(text)["valid"] is True

    def test_parseo_mal_levanta_error(self):
        try:
            _parse_gemini_response("esto no es json")
            assert False, "deberia haber lanzado ValueError"
        except ValueError:
            pass


class _StubClient:
    def __init__(self, text, delay=0.0):
        self._text = text
        self._delay = delay

    @property
    def models(self):
        import time

        class _Models:
            def __init__(self, text, delay):
                self._text = text
                self._delay = delay

            def generate_content(self, model, contents):
                if self._delay:
                    time.sleep(self._delay)
                return type("R", (), {"text": self._text})()

        return _Models(self._text, self._delay)


class TestPipeline:
    def test_gemini_ok_con_validator_gemini(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.setenv("NLP_VALIDATOR", "gemini")
        monkeypatch.setattr(
            nlp_validator,
            "_gemini_client",
            lambda: _StubClient(
                '{"word_found": true, "has_verb": true, "token_count": 6, '
                '"details": "Correcta", "suggestion": null}'
            ),
        )
        result, used = validate_sentence_pipeline("apple", "I eat an apple every day")
        assert used == "gemini"
        assert result["valid"] is True
        assert result["suggestion"] is None

    def test_gemini_falla_y_cae_a_spacy(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.setenv("NLP_VALIDATOR", "gemini")

        def raiser():
            raise RuntimeError("API caida")

        monkeypatch.setattr(nlp_validator, "_gemini_client", raiser)
        result, used = validate_sentence_pipeline("apple", "I eat an apple every day")
        assert used == "spacy"
        assert result["valid"] is True

    def test_spacy_config_no_llama_gemini(self, monkeypatch):
        monkeypatch.setenv("NLP_VALIDATOR", "spacy")

        def should_not_be_called():
            raise AssertionError("no debe llamarse Gemini")

        monkeypatch.setattr(nlp_validator, "_gemini_client", should_not_be_called)
        result, used = validate_sentence_pipeline("apple", "I eat an apple every day")
        assert used == "spacy"
        assert result["valid"] is True

    def test_sin_oracion_no_llama_nada(self, monkeypatch):
        monkeypatch.setenv("NLP_VALIDATOR", "gemini")

        def should_not_be_called():
            raise AssertionError("no debe llamarse Gemini")

        monkeypatch.setattr(nlp_validator, "_gemini_client", should_not_be_called)
        result, used = validate_sentence_pipeline("apple", "  ")
        assert used == "spacy"
        assert result["valid"] is False

    def test_gemini_lento_cae_a_spacy_dentro_del_presupuesto(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.setenv("NLP_VALIDATOR", "gemini")
        monkeypatch.setattr(
            nlp_validator,
            "get_gemini_timeout_ms",
            lambda: 40,
        )
        monkeypatch.setattr(
            nlp_validator,
            "_gemini_client",
            lambda: _StubClient(
                '{"word_found": true, "has_verb": true, "token_count": 6, '
                '"details": "Correcta", "suggestion": null}',
                delay=0.3,
            ),
        )
        import time

        t0 = time.perf_counter()
        result, used = validate_sentence_pipeline("apple", "I eat an apple every day")
        elapsed = time.perf_counter() - t0
        assert used == "spacy"
        assert result["valid"] is True
        assert elapsed < 0.25, f"tardo {elapsed:.3f}s en vez de caer rapido"


class TestQuizIntegration:
    _JSON_INVALIDA = (
        '{"word_found": false, "has_verb": true, "token_count": 5, '
        '"details": "Falta la palabra", "suggestion": "I like eating an apple."}'
    )
    _JSON_VALIDA = (
        '{"word_found": true, "has_verb": true, "token_count": 6, '
        '"details": "Correcta", "suggestion": null}'
    )

    def _post_quiz(self, client, word_id):
        return client.post(
            "/study/quiz",
            data={
                "word_id": word_id,
                "english_answer": "apple",
                "sentence": "I like apple day",
                "direction": "es_to_en",
            },
            follow_redirects=False,
        )

    def _last_history(self, app):
        with app.app_context():
            return SessionHistory.query.order_by(SessionHistory.id.desc()).first()

    def test_quiz_gemini_guarda_validator_y_sugerencia(self, app, client, make_word, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.setenv("NLP_VALIDATOR", "gemini")
        monkeypatch.setattr(nlp_validator, "_gemini_client", lambda: _StubClient(self._JSON_INVALIDA))
        word_id = make_word("apple", "manzana")
        resp = self._post_quiz(client, word_id)
        assert resp.status_code == 302
        h = self._last_history(app)
        assert h.validator_source == "gemini"
        assert h.sentence_suggestion == "I like eating an apple."
        assert h.sentence_valid is False

    def test_result_muestra_badge_ia_y_sugerencia(self, app, client, make_word, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.setenv("NLP_VALIDATOR", "gemini")
        monkeypatch.setattr(nlp_validator, "_gemini_client", lambda: _StubClient(self._JSON_INVALIDA))
        word_id = make_word("apple", "manzana")
        resp = self._post_quiz(client, word_id)
        body = client.get(resp.headers["Location"]).data.decode()
        assert "Validada con IA" in body
        assert "Sugerencia" in body
        assert "I like eating an apple." in body

    def test_quiz_gemini_valida_guarda_sin_sugerencia(self, app, client, make_word, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.setenv("NLP_VALIDATOR", "gemini")
        monkeypatch.setattr(nlp_validator, "_gemini_client", lambda: _StubClient(self._JSON_VALIDA))
        word_id = make_word("apple", "manzana")
        resp = self._post_quiz(client, word_id)
        assert resp.status_code == 302
        h = self._last_history(app)
        assert h.validator_source == "gemini"
        assert h.sentence_valid is True
        assert h.sentence_suggestion is None

    def test_quiz_gemini_falla_cae_a_spacy(self, app, client, make_word, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.setenv("NLP_VALIDATOR", "gemini")

        def raiser():
            raise RuntimeError("API caida")

        monkeypatch.setattr(nlp_validator, "_gemini_client", raiser)
        word_id = make_word("apple", "manzana")
        resp = self._post_quiz(client, word_id)
        assert resp.status_code == 302
        h = self._last_history(app)
        assert h.validator_source == "spacy"
        assert h.sentence_suggestion is None