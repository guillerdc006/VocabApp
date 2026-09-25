"""Backup de la base real (SQLite) antes de cualquier cambio.

Uso:
    python3 scripts/backup_db.py

Genera instance/vocabulary.db.bak-YYYYMMDD-HHMMSS usando la API de backup de
SQLite (segura con WAL, a diferencia de cp).

Regla: SIEMPRE ejecutar este script antes de tocar la BD real. Nunca ejecutar
debug/tests contra ella. Ver AGENTS.md.
"""
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def main() -> int:
    project = Path(__file__).resolve().parent.parent
    db_path = project / "instance" / "vocabulary.db"
    if not db_path.exists():
        print(f"No existe la base: {db_path}")
        return 1

    dest = db_path.parent / f"vocabulary.db.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    src = sqlite3.connect(db_path)
    dst = sqlite3.connect(dest)
    try:
        src.backup(dst)
    except Exception as exc:  # noqa: BLE001
        print(f"Error al crear el backup: {exc}")
        return 1
    finally:
        dst.close()
        src.close()

    with sqlite3.connect(dest) as check:
        n_words = check.execute("SELECT COUNT(*) FROM words").fetchone()[0]
    print(f"Backup creado y verificado: {dest.name} (words={n_words})")
    return 0


if __name__ == "__main__":
    sys.exit(main())