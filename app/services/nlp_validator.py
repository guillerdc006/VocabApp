import json

import spacy

from ..config import get_api_key, get_model, get_validator

_nlp = None

_GEMINI_TIMEOUT_MS = 20000


def get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


def resolve_validator():
    """Proveedor establecido: 'gemini' solo si esta activado y hay clave, si no 'spacy'."""
    if get_validator() == "gemini" and get_api_key():
        return "gemini"
    return "spacy"


def validate_answer(word_english, user_answer):
    return word_english.strip().lower() == user_answer.strip().lower()


def validate_sentence_pipeline(word_english, sentence):
    """Valida con el proveedor configurado. Sin oracion -> invalida (spacy).

    Returns (result_dict, validator_used). Ante cualquier fallo de Gemini
    (red, API, parseo) cae a spaCy sin romper el flujo.
    """
    if not sentence:
        return {"valid": False, "details": "No se escribio oracion"}, "spacy"

    if resolve_validator() == "gemini":
        try:
            return _gemini_validate_sentence(word_english, sentence), "gemini"
        except Exception:
            pass

    return validate_sentence(word_english, sentence), "spacy"


def _gemini_client():
    from google.genai import Client, types

    return Client(
        api_key=get_api_key(),
        http_options=types.HttpOptions(timeout=_GEMINI_TIMEOUT_MS),
    )


def _build_gemini_prompt(word_english, sentence):
    return (
        "You are an English grammar and vocabulary checker for a Spanish-English vocabulary app.\n"
        f"Target word or phrase: {word_english!r}\n"
        f"User sentence: {sentence!r}\n"
        "Check and answer ONLY with JSON (no markdown):\n"
        "1. word_found: does the target word/phrase appear in the sentence? "
        "Allow natural inflections (go -> went/gone/going; take off -> took off). "
        "Phrase words must appear consecutively and in order.\n"
        "2. has_verb: does the sentence have at least one main verb? (a modal/aux verb alone does not count).\n"
        "3. token_count: number of meaningful words (ignore punctuation).\n"
        "4. details: short explanation in Spanish of any problem (or 'Correcta' if the sentence is fine).\n"
        "5. suggestion: if there is any problem, one corrected example sentence that does use the target word; "
        "if the sentence is fine, use null.\n"
        'Return: {"word_found": bool, "has_verb": bool, "token_count": int, '
        '"details": string, "suggestion": string|null}'
    )


def _parse_gemini_response(text):
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("Respuesta de Gemini sin JSON")
    data = json.loads(text[start:end + 1])
    word_found = bool(data.get("word_found", False))
    has_verb = bool(data.get("has_verb", False))
    token_count = int(data.get("token_count", 0))
    has_min_length = token_count >= 3
    is_valid = word_found and has_verb and has_min_length
    suggestion = data.get("suggestion")
    if suggestion is not None and str(suggestion).strip() in ("", "null", "None"):
        suggestion = None
    return {
        "valid": is_valid,
        "word_found": word_found,
        "word_info": {"text": None, "lemma": None, "pos": None, "dep": None},
        "has_verb": has_verb,
        "has_noun_or_pronoun": None,
        "token_count": token_count,
        "details": data.get("details") or _build_feedback(
            is_valid, word_found, has_verb, has_min_length, "target"
        ),
        "suggestion": suggestion,
    }


def _gemini_validate_sentence(word_english, sentence):
    client = _gemini_client()
    response = client.models.generate_content(
        model=get_model(),
        contents=_build_gemini_prompt(word_english, sentence),
    )
    return _parse_gemini_response(response.text)


def validate_sentence(word_english, sentence):
    nlp = get_nlp()
    doc = nlp(sentence)
    word_lower = word_english.lower().strip()
    sentence_lower = sentence.lower().strip()
    tokens_lower = [t.text.lower() for t in doc if not t.is_space]

    word_found = False
    word_info = None

    if word_lower in sentence_lower:
        word_found = True
        word_tokens = word_lower.split()
        for i, token in enumerate(doc):
            if token.text.lower() == word_tokens[0]:
                match = True
                for j in range(1, len(word_tokens)):
                    if i + j >= len(doc) or doc[i + j].text.lower() != word_tokens[j]:
                        match = False
                        break
                if match:
                    word_info = {
                        "text": " ".join(t.text for t in doc[i:i + len(word_tokens)]),
                        "lemma": " ".join(t.lemma_ for t in doc[i:i + len(word_tokens)]),
                        "pos": doc[i].pos_,
                        "dep": doc[i].dep_,
                    }
                    break

    tokens = [t for t in doc if not t.is_punct and not t.is_space]
    has_verb = any(t.pos_ in ("VERB", "AUX") for t in tokens)
    has_noun_or_pronoun = any(t.pos_ in ("NOUN", "PROPN", "PRON") for t in tokens)
    has_min_length = len(tokens) >= 3

    is_valid = word_found and has_verb and has_min_length

    return {
        "valid": is_valid,
        "word_found": word_found,
        "word_info": word_info,
        "has_verb": has_verb,
        "has_noun_or_pronoun": has_noun_or_pronoun,
        "token_count": len(tokens),
        "details": _build_feedback(is_valid, word_found, has_verb, has_min_length, word_english),
    }


def _build_feedback(is_valid, word_found, has_verb, has_min_length, word):
    if is_valid:
        return "Oracion valida. La palabra esta correctamente utilizada."

    issues = []
    if not word_found:
        issues.append(f'La palabra "{word}" no aparece en la oracion')
    if not has_verb:
        issues.append("La oracion no tiene verbo")
    if not has_min_length:
        issues.append("La oracion es muy corta (minimo 3 palabras)")

    return " | ".join(issues)
