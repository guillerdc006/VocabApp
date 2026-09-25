import os
from pathlib import Path

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import event
from sqlalchemy.engine import Engine

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REAL_DB_PATH = (PROJECT_ROOT / "instance" / "vocabulary.db").resolve()


def _is_real_db(file_path):
    """True si el path (engine URL database) es la base real de produccion."""
    if not file_path:
        return False
    return Path(str(file_path)).expanduser().resolve() == REAL_DB_PATH


class GuardedSQLAlchemy(SQLAlchemy):
    """Bloquea drop_all contra la base real salvo flag explicito.

    Solamente se protegen operaciones DESTRUCTIVAS (drop_all). create_all no se
    bloquea: es idempotente sobre la BD real y la usa create_app() al arrancar.
    """

    def _guard_destructive(self, operation):
        if os.environ.get("ALLOW_DESTRUCTIVE_OPERATIONS") == "1":
            return
        try:
            engines = list(self.engines.values())
        except RuntimeError:
            return
        if any(_is_real_db(engine.url.database) for engine in engines):
            raise RuntimeError(
                f"[GUARD] '{operation}' bloqueado: un motor apunta a la base real "
                f"({REAL_DB_PATH.name}). Solo destruirla de forma intencional con "
                "ALLOW_DESTRUCTIVE_OPERATIONS=1 (ver AGENTS.md)."
            )

    def drop_all(self, bind_key="__all__", **kwargs):
        self._guard_destructive("drop_all")
        return super().drop_all(bind_key=bind_key, **kwargs)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
    finally:
        cursor.close()


db = GuardedSQLAlchemy()
migrate = Migrate()