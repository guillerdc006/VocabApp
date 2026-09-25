import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.extensions import db
from app.services.excel_import import import_file


def main():
    filepath = sys.argv[1] if len(sys.argv) > 1 else "Vocabulary.xlsx"

    if not os.path.exists(filepath):
        print(f"Error: No se encontro el archivo '{filepath}'")
        sys.exit(1)

    app = create_app()
    with app.app_context():
        print(f"Importando desde: {filepath}")
        added, skipped = import_file(filepath)
        print(f"Importacion completa:")
        print(f"  - {added} palabras agregadas")
        print(f"  - {skipped} duplicadas omitidas")

        total = db.session.query(db.func.count()).select_from(db.Table("words", db.metadata, autoload_with=db.engine)).scalar()
        print(f"  - Total en base de datos: {total}")


if __name__ == "__main__":
    main()
