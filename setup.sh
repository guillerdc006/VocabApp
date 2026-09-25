#!/bin/bash
set -e

echo "=== VocabApp - Instalacion ==="

echo "1. Instalando dependencias..."
pip install -r requirements.txt

echo "2. Descargando modelo de spaCy (en_core_web_sm)..."
python -m spacy download en_core_web_sm

echo "3. Inicializando base de datos..."
python -c "from app import create_app; from app.extensions import db; app=create_app(); app.app_context().push(); db.create_all(); print('DB creada en instance/vocabulary.db')"

echo ""
echo "=== Instalacion completa ==="
echo "Para importar el Excel:  python import_excel.py"
echo "Para ejecutar la app:    python run.py"
echo "La app estara en:        http://127.0.0.1:5000"
