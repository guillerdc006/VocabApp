# AGENTS.md

Instrucciones para trabajar en VocabApp (web de repaso de vocabulario EN/ES con
SM-2, NLP y panel de estadisticas).

## Base de datos real (PRODUCCION)
- La base real es `instance/vocabulary.db` (SQLite en modo WAL). Contiene los datos del
  usuario (palabras, progreso, historial). **NUNCA se toca en pruebas ni debug.**

- ⚠️ PATRON PROHIBIDO (causa real de perdida de datos): crear la app con la config por
  defecto y luego intentar apuntar a otra base reasignando la config:

  ```python
  app = create_app()                                  # motor enlazado a vocabulary.db
  app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tmp.db"   # YA ES TARDE
  db.drop_all()                                       # borra la BD REAL
  ```

  El motor SQLAlchemy queda enlazado a la BD real y `drop_all()/create_all()` la destruyen.

- PATRON SEGURO: pasar la config DENTRO de `create_app`, igual que `tests/conftest.py`:

  ```python
  app = create_app(UnConfigConSQLiteTemporal)   # por referencia ver tests/conftest.py
  ```

- GUARDA DE SEGURIDAD: `db.drop_all()` esta bloqueado por `GuardedSQLAlchemy`
  (`app/extensions.py`) cuando el motor apunta a la base real. Si un dia se necesita
  destruirla a proposito, usar `ALLOW_DESTRUCTIVE_OPERATIONS=1` (NUNCA por error).

- `flask db upgrade` (migraciones) SI es seguro contra la BD real: usa Alembic, no
  `drop_all()`. Antes de crearla/ejecutarla igualmente hacer backup (regla de abajo).

## Backup OBLIGATORIO antes de cualquier cambio sobre la BD real
Antes de MIGRACIONES, cambios de modelo, scripts o depuracion que puedan escribir en la
BD real, ejecutar SIEMPRE:

    python3 scripts/backup_db.py

- Usa la API `sqlite3.Connection.backup()` (segura con WAL; `cp` NO lo es).
- Genera `instance/vocabulary.db.bak-YYYYMMDD-HHMMSS` y verifica el conteo de `words`.
- Si el script falla o no se crea el archivo: DETENERSE y avisar al usuario.

## Zona horaria (UTC)
- Todos los timestamps (`created_at`, `next_review`, `last_practiced`) y todos los cortes de
  "hoy"/dias en analitica se calculan en **UTC** (`datetime.now(timezone.utc)`), por decision
  del usuario. NO convertir a hora local salvo que lo pida el usuario.
- El sistema esta en `America/Guayaquil` (UTC-5): el dia UTC rueda a las **19:00 hora local**.
  Entre 19:00 y 00:00 local, cualquier practica se registra con la fecha UTC del dia siguiente.

## Pruebas
- Los tests usan una BD temporal aislada por test (`tmp_path`, ver `tests/conftest.py`).
  Nunca tocan `instance/vocabulary.db`.
- Ejecutar la suite completa y dejar TODO verde antes de dar un paso por terminado:

    export PATH="$HOME/.local/bin:$PATH"
    python3 -m pytest

## Entorno / servidor
- Instalar dependencias con `pip --break-system-packages` (Python 3.14 del sistema).
- Levantar el servidor (puerto 5000) con:

    setsid python3 -c "from app import create_app; app=create_app(); app.run(host='127.0.0.1', port=5000, debug=False)" > /tmp/vocabapp.log 2>&1 &

- Detenerlo con: `fuser -k 5000/tcp`.
- Tras cambios de codigo, reiniciar el servidor antes de verificar en el navegador.

## Flujo de trabajo por paso
1. Backup de la BD real (`python3 scripts/backup_db.py`).
2. Implementar el cambio e informar al usuario su funcion/purpose.
3. Agregar tests de unidad/la funcion nueva en `tests/`.
4. Suite completa verde (`python3 -m pytest`).
5. Reiniciar servidor y verificar en vivo.
6. Actualizar changelog en README.md (seccion "Changelog") y Uso si aplica.