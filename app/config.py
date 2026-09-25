import os

from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))

load_dotenv(os.path.join(basedir, "..", ".env"))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "vocabapp-dev-secret-key-change-in-production")
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "..", "instance", "vocabulary.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    GEMINI_API_KEY = ""  # el runtime toma la clave de os.environ (.env), aqui solo se documenta
    NLP_VALIDATOR = "gemini"
    GEMINI_MODEL = "gemini-3.6-flash"


def get_api_key():
    """Clave de Gemini desde el entorno (.env). Vacia si no esta configurada."""
    return os.environ.get("GEMINI_API_KEY", Config.GEMINI_API_KEY)


def get_validator():
    """Proveedor NLP activo: 'gemini' o 'spacy'."""
    return os.environ.get("NLP_VALIDATOR", Config.NLP_VALIDATOR)


def get_model():
    """Modelo de Gemini a usar (configurable via .env)."""
    return os.environ.get("GEMINI_MODEL", Config.GEMINI_MODEL)