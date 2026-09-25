# VocabApp

> App web on-premise para repasar vocabulario ingles-espanol con **spaced repetition** y **verificacion NLP**.

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![spaCy](https://img.shields.io/badge/spaCy-NLP-09A3D5?style=for-the-badge&logo=spacy&logoColor=white)](https://spacy.io/)
[![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

---

## Descripcion

VocabApp es una aplicacion web disenada para el repaso activo de vocabulario ingles-espanol. Funciona en local (localhost); la unica pieza opcional que usa la nube es la **validacion IA de oraciones con Google Gemini** (se desactiva simplemente no configurando la clave en `.env`).

El usuario presenta una palabra en espanol, escribe su traduccion en ingles y formula una oracion con ella. La app verifica ambas respuestas usando NLP (spaCy, con Gemini opcional) y aplica el algoritmo **SM-2 de Spaced Repetition** para determinar cuando revisar cada palabra nuevamente.

---

## Key Features

- **SM-2 Spaced Repetition** — Words are scheduled for review based on performance. Difficult words appear more often; mastered words are spaced further apart.
- **NLP Sentence Validation** — spaCy validates that the English word (or multi-word expression) appears in the sentence. Supports single words, lemmas, and complete phrases (e.g. "get lost", "show up on time"). Also validates auxiliary verbs (is/are/was/were/be). Optional **Gemini** (AI) validator with automatic fallback adds suggestions for corrected sentences.
- **Excel Bulk Import** — Import hundreds of words at once from an `.xlsx` file via the web UI or CLI.
- **Progress Tracking** — Dashboard, Estadisticas with accuracy metrics, word difficulty levels, session history, and a consolidated server-side report (`/report`) with PDF export.
- **Fully Local** — Runs on `127.0.0.1:5000`. No cloud, no accounts (the only optional cloud piece is the Gemini validator).

---

## Caracteristicas

| Funcionalidad | Descripcion |
|---|---|
| **Quiz interactivo** | Muestra palabra en espanol → el usuario escribe la traduccion en ingles → escribe una oracion |
| **Verificacion NLP** | spaCy verifica: palabra/frase presente, verbos (VERB + AUX: is/are/was/were/be), minimo 3 tokens |
| **Sistema de niveles** | 4 niveles: Nueva, Facil, Media, Dificil — con progresion automatica |
| **SM-2 Spaced Repetition** | Algoritmo SuperMemo 2: ajusta intervalo, factor de facilidad y proxima revision |
| **Dashboard** | Resumen: palabras totales, practicadas, precision semanal, pendientes de revision |
| **CRUD de vocabulario** | Agregar, eliminar, buscar y paginar palabras |
| **Importar Excel** | Subir archivo `.xlsx` desde el navegador con drag & drop |
| **Estadisticas** | Palabras mas dificiles, mejor dominadas, historial de sesiones |

---

## Tech Stack

| Componente | Tecnologia | Version |
|---|---|---|
| Backend | Python + Flask | 3.14 / 3.1.1 |
| ORM | Flask-SQLAlchemy | 3.1.1 |
| Migraciones | Flask-Migrate (Alembic) | 4.1.0 |
| Base de datos | SQLite | archivo local |
| NLP | spaCy + en_core_web_sm | 3.8.x |
| Validacion IA | Google Gemini (google-genai) | 2.25.0 |
| Analitica | pandas | 3.0.6 |
| Graficos / PDF | matplotlib (Agg) | 3.11.2 |
| Excel | openpyxl | 3.1.5 |
| Frontend | Bootstrap 5 + Jinja2 | CDN |
| Iconos | Bootstrap Icons | 1.11.3 |

---

## Instalacion

### Requisitos previos

- Python 3.10 o superior
- pip
- (Opcional) Archivo Excel con vocabulario en formato `.xlsx`

### Paso a paso

```bash
# 1. Clonar el repositorio
git clone https://github.com/guillerdc006/VocabApp.git
cd VocabApp

# 2. Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Descargar modelo de spaCy
python -m spacy download en_core_web_sm

# 4b. Clave de Gemini (opcional; activa la validacion IA)
# Crear un archivo .env en la raiz del proyecto (ya esta en .gitignore):
#   GEMINI_API_KEY=tu-clave
#   NLP_VALIDATOR=gemini      # 'spacy' la desactiva
#   GEMINI_TIMEOUT_MS=3000    # presupuesto (ms) para Gemini antes de caer a spaCy

# 5. (Opcional) Importar vocabulario desde Excel
python import_excel.py                          # usa Vocabulary.xlsx por defecto
python import_excel.py ruta/a/tu/archivo.xlsx   # o especificar un archivo

# 6. Ejecutar la aplicacion
python run.py
```

La app estara disponible en: **http://127.0.0.1:5000**

> **Nota:** La base de datos se crea/actualiza automaticamente en `instance/vocabulary.db` (SQLite en modo WAL) al iniciar la app: `create_all()` crea las tablas nuevas y las migraciones Alembic (`flask db upgrade`) versionan los cambios de esquema. Nunca se destruyen datos con `drop_all()` contra la base real.

---

## Uso

### Matcher (`/study/match`)
Empareja hasta 10 palabras espanol/ingles en dos columnas. Al completar las parejas se registra la sesion en el historial (tipo `match`) sin alterar la curva SM-2 del quiz.

### Dashboard (`/`)
Resumen general con total de palabras, practicadas, precision de los ultimos 7 dias, palabras pendientes de revision y tarjeta de carga de repaso (nuevas/vencidas/cola). Incluye accesos rapidos a las funciones principales.

### Quiz (`/study/quiz`)
Muestra palabra en espanol (o en ingles con el selector de direccion), el usuario escribe la traduccion y una oracion. Verificacion NLP y SM-2; la direccion elegida se conserva en la sesion.

Ayudas para recordar (barra bajo la palabra, siempre visibles):
- **Pista** (`bi-lightbulb`): revela la observacion de la palabra. Si no tiene, muestra *"La palabra no tiene observacion."*.
- **No recuerdo / Ver respuesta** (`bi-eye`): rellena la traduccion correcta y la bloquea en solo lectura. La mitad de la palabra se cuenta como incorrecta automaticamente (0 de 50 puntos), aun si el texto despues resulta correcto; la oracion se sigue puntuando con normalidad. La practica queda marcada `was_revealed` y se refleja en Estadisticas como "Practicas con ayuda".

> El resultado se sirve via GET (patron PRG). Recargar la pagina no re-registra la practica ni duplica el conteo.

### Vocabulario (`/vocabulary/`)
Lista paginada (20 por pagina) con busqueda por palabra en ingles o espanol. Permite agregar, editar y eliminar palabras, y exportar todo el vocabulario + progreso a Excel.

### Importar (`/vocabulary/import`)
Subir un archivo `.xlsx` con columnas `english`/`spanish` (o `ingles`/`espanol`). Los duplicados se omiten automaticamente.

### Estadisticas (`/study/stats`)
Precision general, palabras mas dificiles, palabras mejor dominadas e historial completo paginado con filtros (palabra, correctas/incorrectas, tipo de sesion, rango de fechas). Ademas: racha actual y mejor racha de practica, dias activos, precision por tipo de sesion (quiz/matcher), direccion (es-en / en-es) y validador (IA Gemini / spaCy), contador de "practicas con ayuda" (respuesta revelada), panel de carga de repaso SM-2 (nuevas/vencidas/cola, repasos programados a 14 dias, ritmo diario y proyeccion), grafico de evolucion de precision (30 dias, con serie por tipo) y calendario de actividad (16 semanas).

### Informe (`/report`)
Reporte consolidado de progreso generado en servidor (pandas para el analisis, matplotlib para los graficos): metricas clave, resumen de practica, carga de repaso, precision por tipo/direccion/validador, evolucion de 30 dias, calendario de actividad, distribucion por nivel SM-2, repasos programados a 14 dias y tablas de palabras mas dificiles / mejor dominadas. Boton **"Descargar PDF"** (`/report/pdf`) para exportarlo como informe multipagina (informe-progreso-YYYYMMDD.pdf).

> **Zona horaria (UTC):** todos los timestamps y cortes de "hoy" se calculan en **UTC**. El sistema corre en `America/Guayaquil` (UTC-5), por lo que el dia UTC rueda a las **19:00 hora local**: entre 19:00 y medianoche local, una practica se registra con la fecha UTC del dia siguiente.

### Diccionario de mediciones
[`MEDICIONES.md`](MEDICIONES.md) documenta como se calcula **cada metrica y cada visual** de la app (que mide, formula/definicion, fuente de datos y objetivo), ademas del objetivo de cada servicio. Es la guia de referencia para leer los numeros de la app, para implementar el proyecto desde cero o para presentarlo como portafolio.

### Pruebas (pytest)
```bash
pip install -r requirements-dev.txt   # instala pytest
python -m pytest                       # ejecuta toda la suite
```
Las pruebas usan una base de datos aislada en `/tmp`; nunca modifican `instance/vocabulary.db`.

### Migraciones (Flask-Migrate / Alembic)
```bash
FLASK_APP=run.py flask db init       # una sola vez (ya realizado)
FLASK_APP=run.py flask db migrate -m "descripcion"   # genera la migracion
FLASK_APP=run.py flask db upgrade    # aplica la migracion a la BD
```

---

## Arquitectura

### Application Factory Pattern

```
run.py  →  app/__init__.py (create_app())  →  Blueprints  →  Routes  →  Templates
                              ↓
                    extensions.py (db, migrate: instancias SQLAlchemy + Alembic)
                              ↓
                         models.py (Word, WordStats, SessionHistory)
                              ↓
        services/ (sm2, nlp_validator, excel_import, analytics, reporting)
```

### Blueprints

| Blueprint | Prefijo | Funcion |
|---|---|---|
| `main_bp` | `/` | Dashboard y pagina de inicio |
| `vocab_bp` | `/vocabulary` | CRUD de vocabulario + importacion Excel |
| `study_bp` | `/study` | Quiz, resultado, matcher y estadisticas |
| `report_bp` | `/report` | Informe de progreso y exportacion PDF |

### Database Schema

```
┌──────────────────────────┐     ┌────────────────────────────────┐
│          words           │     │           word_stats            │
├──────────────────────────┤     ├────────────────────────────────┤
│ id (PK)                  │──1:1│ word_id (FK, UNIQUE)            │
│ english (UNIQUE)         │     │ repetitions                     │
│ spanish                  │     │ easiness_factor (SM-2 EF)       │
│ notes                    │     │ interval (dias)                 │
│ created_at               │     │ times_practiced                 │
└──────────────────────────┘     │ times_correct (aciertos totales)│
                                 │ level (0 Nueva..3 Dificil)      │
                                 │ next_review  (UTC, proximo)     │
                                 │ last_practiced (UTC)            │
                                 └────────────────────────────────┘
                                              │
                                ┌─────────────────────────────────┐
                                │         session_history          │
                                ├─────────────────────────────────┤
                                │ id (PK)                         │
                                │ word_id (FK)                    │
                                │ english_answer (lo escrito)     │
                                │ sentence (oracion del usuario)  │
                                │ sentence_details (feedback NLP) │
                                │ sentence_suggestion (IA)        │
                                │ is_correct (mitad palabra)      │
                                │ sentence_valid (mitad oracion)  │
                                │ was_revealed (uso de ayuda)     │
                                │ score (0-110)                   │
                                │ quality (SM-2: 0-5)             │
                                │ session_type (quiz/match)       │
                                │ direction (es_to_en/en_to_es)   │
                                │ validator_source (gemini/spacy) │
                                │ created_at (UTC)                │
                                └─────────────────────────────────┘
```

**Como funciona la base de datos:**

- **Archivo unico SQLite en modo WAL** (`PRAGMA journal_mode=WAL`, `busy_timeout=5000`, `foreign_keys=ON`) en `instance/vocabulary.db`. El modo WAL permite lecturas concurrentes con una sola escritura y es mas resistente a corridas; el backup us `sqlite3.Connection.backup()` (nunca `cp`).
- **Tres tablas relacionales:** `words` (1 palabra) → `word_stats` (1 registro de progreso SM-2 por palabra, relacion 1:1) y `session_history` (N sesiones de practica por palabra). No hay otras tablas.
- **Timestamps en UTC y naive:** todos los registros de tiempo (`created_at`, `next_review`, `last_practiced`) se calculan en `datetime.now(timezone.utc)` y SQLite los guarda como `datetime` sin zona horaria (naive), interpretados siempre como UTC por los servicios de analitica (`analytics.py`, `reporting.py`). No se hace ninguna conversion a hora local.
- **Ciclo de vida:** `db.create_all()` crea las tablas nuevas al arrancar (idempotente), y los cambios de esquema ya presentes se versionan con **Flask-Migrate/Alembic** (`migrations/`), aplicandose con `flask db upgrade`. Nunca se usa `drop_all()` contra la BD real: `GuardedSQLAlchemy` (`extensions.py`) lo bloquea salvo `ALLOW_DESTRUCTIVE_OPERATIONS=1`.
- **Antes de migrar o depurar:** ejecutar `python3 scripts/backup_db.py` (genera `instance/vocabulary.db.bak-YYYYMMDD-HHMMSS` y verifica el conteo de palabras).

### SM-2 Spaced Repetition Algorithm

El algoritmo SM-2 (SuperMemo, 1987) determina la proxima revision de cada palabra basandose en la calidad de la respuesta:

**Calidad (quality)**: 0-5, donde:
- `5` = Respuesta perfecta + oracion valida
- `4` = Respuesta correcta pero oracion invalida
- `3` = Respuesta incorrecta pero oracion valida
- `1` = Ambas incorrectas

**Actualizacion del factor de facilidad (EF)**:
```
EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
EF = max(1.3, EF')
```

**Determinacion del intervalo**:
- Si `q < 3` (fallo): `repeticiones = 0`, `intervalo = 1 dia`
- Si `q >= 3` (exito):
  - 1ra repeticion: `intervalo = 1 dia`
  - 2da repeticion: `intervalo = 6 dias`
  - Siguientes: `intervalo = ceil(intervalo_anterior * EF)`

### NLP Validation Pipeline

La validacion de oraciones tiene **dos proveedores** intercambiables con el mismo
contrato de salida `{ valid, word_found, has_verb, token_count, details, suggestion }`:

1. **IA (Gemini)** — defecto si hay `GEMINI_API_KEY` en `.env` y `NLP_VALIDATOR=gemini`.
   Una llamada a `Models.generate_content` (modelo `gemini-3.6-flash`, configurable) juzga:
   la palabra/frase (permitiendo inflexiones: go -> went/gone), si hay verbo principal y la
   longitud, y cuando la oracion falla devuelve una **sugerencia** de oracion corregida que se
   guarda en el historial y se muestra en el resultado.
2. **Local (spaCy)** — fallback automatico si Gemini no esta configurado, falla o no responde a
   tiempo. No hace sugerencias.

**Latencia garantizada:** la validacion con Gemini corre con un **presupuesto de tiempo**
(`GEMINI_TIMEOUT_MS`, defecto `3000` ms en `.env`). Si la API no responde dentro del presupuesto
(errores del tier gratuito como `429` por cuota o lentitud con demanda alta), se cae a spaCy y el
quiz nunca se queda colgado: el peor caso de espera es el presupuesto y lo tipico es < 1 segundo.
El deadline HTTP por intento queda fijo en `10000` ms (minimo que exige la API; el corte de UX lo
impone el presupuesto). Para esperar mas a Gemini en dias lentos, subir `GEMINI_TIMEOUT_MS`; para
una respuesta aun mas instantanea, bajarlo.

```
Entrada: oracion del usuario + palabra objetivo
                    ↓
  ¿validar con Gemini? (config + clave)
    ├─ Sí ──▶ Gemini API ──▶ { valid, details, suggestion }  (validator_source="gemini")
    └─ No/fallo ──▶ spaCy en_core_web_sm (validator_source="spacy")
                    ↓
    Verificaciones (spaCy):
    ✓ Palabra/frase completa presente en la oracion
      (substring + tokens consecutivos en orden)
    ✓ Oracion contiene al menos un verbo (POS: VERB o AUX)
    ✓ Longitud minima: 3 tokens (sin puntuacion)
                    ↓
    Resultado: { valid: bool, details: str }
```

Cada practica guarda en `SessionHistory` quien valido (`validator_source`) y la sugerencia
(`sentence_suggestion`), lo que permite desglosar precision por validador en Estadisticas
y mostrar el badge "Validada con IA" en el resultado de la practica.

**Soporte multi-palabra:** Expresiones como "get lost", "show up on time" o "to be honest" se validan verificando que todos los tokens aparezcan consecutivamente en la oracion, en el mismo orden.

**Verbos auxiliares:** spaCy etiqueta "is/are/was/were/be" como `AUX` en vez de `VERB`. El validador acepta ambas categorias para no rechazar oraciones correctas como "She is beautiful" o "They were ready".

---

## Estructura del Proyecto

```
VocabApp/
├── run.py                          # Entry point — inicia Flask en localhost:5000
├── requirements.txt                # Dependencias Python
├── requirements-dev.txt            # Dependencias de testing (pytest, spaCy model)
├── setup.sh                        # Script de instalacion automatica
├── import_excel.py                 # CLI para importar Excel
├── Vocabulary.xlsx                 # Dataset de ejemplo (256 palabras)
├── .env                            # Config local (claves Gemini, NLP_VALIDATOR, timeout)
├── .gitignore
├── AGENTS.md                       # Guia de trabajo: BD real, backup, pruebas
├── LICENSE                         # MIT License
│
├── instance/                       # Datos locales (gitignored)
│   ├── vocabulary.db               # Base de datos real (SQLite, WAL)
│   └── vocabulary.db.bak-*         # Backups generados por scripts/backup_db.py
│
├── migrations/                     # Versionado de esquema (Flask-Migrate/Alembic)
│   └── versions/                   # 990ceaa573c9, b6ed4e264721, 7b07b91d82c0, ...
│
├── scripts/
│   └── backup_db.py                # Backup seguro de la BD (sqlite3.backup)
│
├── tests/                          # Suite pytest (BD aislada por test)
│   ├── conftest.py                 # Fixtures app/cliente + suite sin red
│   ├── test_smoke.py               # Smoke tests de todas las rutas
│   ├── test_ia.py                  # Validacion Gemini/spaCy + presupuesto
│   ├── test_report.py              # Informe /report y PDF
│   ├── test_practica_con_ayuda.py  # Boton "No recuerdo / Ver respuesta"
│   ├── test_hint.py, test_reverse_quiz.py, test_match.py, ...
│   └── ...
│
└── app/                            # Paquete principal de la aplicacion
    ├── __init__.py                 # create_app() — Application Factory
    ├── config.py                   # Configuracion (SECRET_KEY, DB URI, Gemini)
    ├── extensions.py               # SQLAlchemy + Migrate (con GuardedSQLAlchemy)
    ├── models.py                   # Modelos: Word, WordStats, SessionHistory
    │
    ├── routes/                     # Blueprints (capa de presentacion)
    │   ├── main.py                 # Dashboard (/)
    │   ├── vocabulary.py           # CRUD + import (/vocabulary/*)
    │   ├── study.py                # Quiz, matcher, stats (/study/*)
    │   └── report.py               # Informe (/report, /report/pdf)
    │
    ├── services/                   # Logica de negocio
    │   ├── sm2.py                  # Algoritmo SM-2 de Spaced Repetition
    │   ├── nlp_validator.py        # Validacion de oraciones (spaCy + Gemini)
    │   ├── excel_import.py         # Lectura de archivos Excel con openpyxl
    │   ├── analytics.py            # Estadisticas (racha, carga, heatmap, ...)
    │   └── reporting.py            # Informe pandas + matplotlib (+PDF)
    │
    ├── templates/                  # Jinja2 templates
    │   ├── base.html               # Layout base (navbar, Bootstrap 5)
    │   ├── main/index.html         # Dashboard
    │   ├── vocabulary/             # list, add, edit, import
    │   ├── study/                  # quiz, result, stats, match
    │   └── report/report.html      # Informe de progreso
    │
    └── static/css/
        └── style.css               # Estilos custom
```

---

## Formato del Excel

El archivo Excel debe tener dos columnas con estos encabezados:

| Columna A | Columna B | Columna C (opcional) |
|---|---|---|
| `english` (o `ingles`) | `spanish` (o `espanol`) | `observacion` (o `notes`) |

Ejemplo:

| english | spanish |
|---|---|
| get lost | perderse |
| nowadays | hoy en dia |
| delighted | encantado |

> Se aceptan variaciones con y sin tildes (`ingles`/`Inglés`, `espanol`/`Español`).

---

## Estudio de caso: que dicen los datos de tu repaso

Este proyecto cierra el ciclo completo de un **analista** en una solucion real. El informe
(`/report` y el PDF descargable) convierte datos crudos en decisiones de estudio. Las metricas se
pueden leer como un conjunto de hipotesis verificables sobre tu aprendizaje:

**1. La carga de repaso es el indicador de sostenibilidad.** SM-2 programa cada palabra; la cola
= palabras nuevas + vencidas pendientes. Si "vencidas hoy + atrasadas" supera lo que despejas por
semana, la cola crece inevitablemente: el panel te lo advierte ("Considera aumentar la practica").
Es el mismo diagnostico que haria un CRM sobre un backlog de clientes.

**2. Precision por tipo, direccion y validador separa los factores.** Las tres tablas de
Estadisticas (y el primer grafico del informe) te dicen *donde* pierdes puntos: si la precision de
`match` es alta pero la de `quiz` baja, el problema es produccion activa (escribir) y no
reconocimiento. Si `en_to_es` cae por debajo de `es_to_en`, el deficit esta en vocabulario
productivo en espanol. Y la tabla por validador separa la dificultad real de la palabra del ruido
del evaluador (una oracion mal validada por spaCy no es un fallo tuyo).

**3. La curva de retencion espaciada.** Juntando la evolucion de 30 dias (por tipo) con el
calendario y la distribucion por nivel, se ve cuantas palabras han superado al menos un repaso
(niveles 1-3) frente a las que siguen en "Nueva" (colas sin tocar). El informe las une en una sola
captura para decidir, por ejemplo, si conviene mas ampliar el ritmo de los repasos o consolidar el
nivel actual.

**4. El registro honesto de la ayuda (`was_revealed`).** Cuando usas "No recuerdo / Ver respuesta",
la respuesta se marca como fallo y se cuenta como "practica con ayuda". Sin ese registro, la
precision real seria optimista: es lo que un buen analista llama un sesgo de reporte. Con el
contador puedes medir cuantas palabras resuelves sin esfuerzo y decidir si el boton se esta
convirtiendo en un atajo.

**5. Interpretacion segura del tiempo.** Todo se registra en UTC (el sistema corre en
`America/Guayaquil`, UTC-5), asi que "hoy" es consistente sin importar la hora local; el informe
lleva la marca de generacion UTC para que una captura analitica sea reproducible y comparable con
otras.

El flujo completo —captura con SM-2 desde cero, mejora continua del evaluador (spaCy -> Gemini con
fallback), rendimiento acotado y reporte autocontenido— muestra como una base de datos de uso
(SQLite) y un pipeline de analitica (pandas + matplotlib) se combinan en un producto pequeno pero
completo.

---

## Changelog

### v1.20 (2026-09-25) — Informe de progreso (`/report`) y export PDF
- Nueva ruta `/report` con informe consolidado generado en servidor: metricas clave, resumen de practica (precision quiz, oraciones validas, puntaje promedio, practicas con ayuda, ritmo), carga de repaso, cinco graficos (precision por tipo/direccion/validador, evolucion 30 dias, calendario de actividad 16 semanas, distribucion por nivel SM-2 y repasos programados 14 dias) y tablas de palabras mas dificiles / mejor dominadas.
- El analisis se arma con **pandas** (agregaciones por tipo, direccion y validador; distribucion de niveles; listas de rendimiento) y los graficos se renderizan con **matplotlib** (backend `Agg`, sin ventanas). Una misma pasada genera los PNG incrustados de la web y el **PDF multipagina** descargable en `/report/pdf` (informe-progreso-YYYYMMDD.pdf) con resolucion A4.
- Nuevas dependencias pineadas: `pandas==3.0.6` y `matplotlib==3.11.2`.
- Solo lectura de la BD: el informe nunca escribe datos. Tests en `tests/test_report.py` (5). Suite completa **118 passed**.

### v1.19.1 (2026-09-25) — Latencia de validacion acotada
- La validacion con Gemini corre ahora con un **presupuesto de tiempo** (`GEMINI_TIMEOUT_MS`, defecto `3000` ms, configurable en `.env`): si la API no responde a tiempo (por ejemplo `429` por cuota o lentitud por demanda alta del tier gratuito), la validacion cae a spaCy y el quiz nunca se cuelga. El deadline HTTP por intento queda en `10000` ms (minimo que exige la API) y el corte de UX lo impone el presupuesto.
- Antes la espera podia llegar a 10-20 s (deadline de 20 s + reintentos). Ahora el peor caso es el presupuesto y lo tipico es < 1 s.
- Nuevos tests: config del timeout (default/env/invalido) y caida rapida a spaCy si Gemini tarda. Suite completa **113 passed**.
- Se establecio control de versiones Git con punto de retorno `5efd638` (v1.19 completo, antes de este cambio).

### v1.19 (2026-09-25) — Ayuda al recordar en la practica
- La pista ("Mostrar pista") ahora este **siempre visible** en el quiz, tambien para palabras sin observacion: en ese caso muestra "La palabra no tiene observacion."
- Nuevo boton "No recuerdo / Ver respuesta" junto a la pista: rellena la traduccion correcta en solo lectura y **marca la mitad de la palabra como incorrecta automaticamente** (0/50), aunque el texto coincida con la respuesta; la oracion sigue puntuando (Gemini/spaCy) y SM-2 da calidad 3 si es valida.
- Nueva columna `was_revealed` en `session_history` (migracion Alembic `7b07b91d82c0`, con backup previo). El resultado muestra el aviso "Usaste ayuda" y Estadisticas suma el contador "Practicas con ayuda".
- Tests en `tests/test_practica_con_ayuda.py` (7) y `tests/test_hint.py` actualizado. Suite completa **109 passed**.

### v1.18 (2026-09-25) — Validacion IA de oraciones (Gemini + spaCy)
- Config IA: carga de `.env` via `python-dotenv`, claves `GEMINI_API_KEY`, `NLP_VALIDATOR` (default `gemini`) y `GEMINI_MODEL` (default `gemini-3.6-flash`) en `app/config.py`, con helpers `get_api_key()`/`get_validator()`/`get_model()`. SDK `google-genai==2.25.0` pineado en `requirements.txt`.
- Dispatcher en `app/services/nlp_validator.py`: misma firma/contrato de salida para ambos proveedores. `_gemini_validate_sentence()` juzga palabra (con inflexiones), verbo principal y longitud, y devuelve `suggestion` cuando algo falla; timeout de 20 s y fallback automatico a spaCy ante cualquier error o 503 por alta demanda.
- El quiz guarda `validator_source` (`gemini`/`spacy`) y `sentence_suggestion` en `SessionHistory` (columnas ya existentes, sin migraciones). El resultado muestra el badge "Validada con IA" y la sugerencia corregida.
- Estadisticas: nueva tabla "Precision por validador" (IA Gemini vs local spaCy, con conteo de sesiones).
- La suite de tests queda hermeticamente sin red (fixture autouse en `conftest.py`) y con el cliente de Gemini mockeado. Tests en `tests/test_ia.py` (13): config, parser, pipeline, integration del quiz.
- README: seccion NLP Validation Pipeline actualizada y guia de instalacion con `.env`.

### v1.17.1 (2026-09-25) — Zona horaria documentada
- Documentado (README y AGENTS.md) que todos los timestamps y cortes de "hoy"/dias en analitica se calculan en **UTC**; el sistema corre en `America/Guayaquil` (UTC-5) y el dia UTC rueda a las 19:00 hora local. Sin cambios de codigo ni BD.

### v1.17 (2026-09-24) — Carga de repaso (SM-2)
- Nuevo panel "Carga de repaso (SM-2)" en Estadisticas: Nuevas pendientes, Vencidas (hoy + atrasadas) y Cola total, con nota de contexto ("sin tu practica de hoy la cola seria X; hoy despejaste Y"), proyeccion de dias para despejar la cola segun el ritmo promedio (7 dias) y aviso "considera aumentar la practica" si las vencidas superan lo que se despeja a la semana.
- Grafico de barras de repasos programados en los proximos 14 dias y de palabras despejadas por dia (7 dias), ambos con Chart.js via CDN.
- Tarjeta resumen compacta en el Dashboard (`/`) con enlace al detalle.
- La evolucion de precision (30 dias) ahora separa por tipo: serie Quiz y serie Matcher en el mismo grafico (cada tipo solo se dibuja si tuvo actividad).
- `app/services/analytics.py`: `daily_accuracy_by_type()`, `review_skyline()`, `daily_practice_rate()`. Tests en `tests/test_carga_repaso.py` (7) + `test_visualizations.py` ampliado.

### v1.16 (2026-09-24) — Quiz direccion inversa
- Selector de direccion en el quiz: espanol->ingles (default) o ingles->espanol. Con esta ultima se muestra la palabra en ingles y se pide la traduccion al espanol; la oracion sigue validandose en ingles (NLP).
- La direccion elegida se guarda en la sesion y en cada sesion de historial (`direction=en_to_es`), alimentando la precision por direccion de Estadisticas. El resultado muestra la palabra y respuesta correcta segun la direccion.
- Tests en `tests/test_reverse_quiz.py` (7).

### v1.15 (2026-09-24) — Modo matching
- Nuevo modo de practica tipo matcher: emparejar hasta 10 palabras (espanol/ingles) en dos columnas. Seleccion recalca el elegido, los aciertos se marcan en verde y los errores en rojo; al completar todas las parejas se guarda la sesion en el historial con `session_type=match`.
- El matcher registra actividad en el historial y alimenta las estadisticas (precision por tipo), pero NO altera la curva SM-2 (`next_review`/niveles siguen gestionados por el quiz).
- Rutas `GET/POST /study/match[/complete]`, template `study/match.html`, acceso desde navbar y dashboard. Tests en `tests/test_match.py`.

### v1.14 (2026-09-24) — Visualizaciones (Estadisticas)
- Grafico de evolucion de precision de los ultimos 30 dias (Chart.js via CDN) con tooltip por dia (precision y sesiones).
- Calendario de actividad tipo heatmap de las ultimas 16 semanas (intensidad segun sesiones diarias) con leyenda y tooltips. Dias en UTC, consistente con las rachas.
- `app/services/analytics.py`: funciones `daily_accuracy()` y `activity_weeks()`. Tests en `tests/test_visualizations.py`.

### v1.13.3 (2026-09-24) — Guarda de seguridad
- `GuardedSQLAlchemy` bloquea `db.drop_all()` cuando el motor apunta a la base real (`instance/vocabulary.db`), salvo `ALLOW_DESTRUCTIVE_OPERATIONS=1`. `create_all` no se bloquea (idempotente; lo usa el arranque). Verificado en vivo: la BD real no se toco.
- Tests en `tests/test_guard.py` (reconocimiento de la BD real, blqueo y bypass por flag).

### v1.13.2 (2026-09-24) — Herramientas
- Nuevo `scripts/backup_db.py`: backup seguro de la BD real (API `sqlite3.backup`) con verificacion de conteo. Ejecutar antes de cualquier cambio.
- Nuevo `AGENTS.md` con el contexto para evitar la perdida de datos: patron de conexion seguro (config dentro de `create_app`, nunca reasignar el URI despues), backup obligatorio previo y referencia a `tests/conftest.py`.

### v1.13.1 (2026-09-24) — Recuperacion de datos
- Incidencia: un script de depuracion ejecuto `drop_all()`/`create_all()` contra la base real (el motor SQLAlchemy ya apuntaba a ella), vaciando las tablas.
- Recuperacion: restaurada la base desde el backup `vocabulary.db.bak-20260918-1200` (305 palabras, 305 registros de progreso, 210 sesiones) y reaplicada la migracion `b6ed4e264721` (columnas de sesion enriquecida).
- Nuevo backup inmediato: `vocabulary.db.bak-20260924-2200`.
- Precaución para depurar: montar la BD temporal dentro de `create_app` (via config), nunca reasignar `SQLALCHEMY_DATABASE_URI` despues de su creacion.

### v1.13 (2026-09-24)
- **Estadisticas:** Nuevas metricas de analisis: racha actual (dias consecutivos de practica), mejor racha historica, dias activos y precision segmentada por tipo de sesion y direccion de repaso. Tiempos de practica tratados en UTC para evitar desfases de zona horaria.

### v1.12 (2026-09-18)
- **Estadisticas:** Historial completo paginado (20 por pagina) con filtros por palabra, resultado (correctas/incorrectas), tipo de sesion y rango de fechas — reemplaza el listado fijo de las 20 ultimas. Nuevas columnas Tipo y Validador.

### v1.11 (2026-09-18)
- **Datos:** `session_history` enriquecido con `session_type` (quiz/match), `direction` (es_to_en/en_to_es), `validator_source` (spacy/ai) y `sentence_suggestion`. Migracion aplicada: las sesiones historicas quedaron con valores por defecto coherentes. Base para la analitica multi-modo y la validacion IA.

### v1.10 (2026-09-18)
- **Export Excel:** Boton "Exportar" en el listado — descarga `vocabulario_export.xlsx` con palabras + observaciones + progreso (nivel, veces practicada, correctas, precision, proxima revision). Archivo re-importable sin duplicar (round-trip).

### v1.9 (2026-09-18)
- **Import Excel:** Soporte de 3ra columna opcional (`observacion` / `notes`) para cargar pistas junto con las palabras. Sin la columna, el import funciona igual que antes.

### v1.8 (2026-09-17)
- **Quiz:** Boton "Mostrar pista" en el quiz — si la palabra tiene observacion, revela la pista al hacer clic (oculta por defecto para no regalar la respuesta).

### v1.7 (2026-09-17)
- **CRUD:** Edicion de palabras desde la lista (`/vocabulary/edit/<id>`) — permite corregir ingles, espanol y observacion **sin perder stats ni historial**. Boton de lapiz en cada fila.
- **CRUD:** Campo "Observacion / pista" disponible tambien al agregar palabras.

### v1.6 (2026-09-17)
- **Datos:** Campo `notes` (observacion / pista) agregado al modelo `Word` via migracion Flask-Migrate. No se pierde ningun dato existente.
- **Calidad:** Flask-Migrate (Alembic) activado oficialmente — nuevas migraciones en `migrations/`. Los cambios de esquema ahora son versionados y reversibles.

### v1.5 (2026-09-17)
- **Calidad:** Infraestructura de pruebas con pytest — BD de prueba aislada en memoria (no toca `instance/vocabulary.db`), fixtures de app/cliente.
- **Calidad:** Smoke tests de todas las rutas (dashboard, quiz, resultado, estadisticas, CRUD, busqueda, paginacion, import Excel). Suite verde como baseline antes de nuevas funciones.

### v1.4 (2026-09-11)
- **Quiz:** Las palabras nunca practicadas (`next_review IS NULL`) ahora tienen prioridad sobre las pendientes de re-revision SM-2. Se agotan las nuevas antes de volver a aparecer las vencidas.
- **Datos:** Reparada la palabra "get lost" (id 1), cuyos campos SM-2 quedaron desincronizados tras una limpieza previa (contaba con `next_review` definido pero `times_practiced=0`), quedando invisible en ambas tarjetas del dashboard. Restablecidos sus campos a estado de palabra nunca practicada.

### v1.3 (2026-09-11)
- **Dashboard:** Tarjeta "Practicadas" renombrada a "Palabras practicadas" (palabras distintas con al menos 1 practica).
- **Dashboard:** Nueva tarjeta "Oraciones practicadas" con el total de sesiones (oraciones escritas).
- **Dashboard:** Tarjeta "Para practicar" reemplazada por "Pendientes para practica" — muestra solo las palabras que nunca han sido repasadas (`next_review IS NULL`), eliminando la ambiguedad con las palabras pendientes de re-revision SM-2.

### v1.2 (2026-08-24)
- **Fix:** Patron PRG (POST-redirect-GET) — el resultado del quiz ahora se sirve via GET en `/study/result/<id>`. Evita el doble conteo al recargar la pagina (F5) o reenviar el formulario.
- **Fix:** SQLite configurado con `PRAGMA journal_mode=WAL`, `busy_timeout=5000` y `foreign_keys=ON` — elimina errores `database is locked` que impedian registrar practicas bajo peticiones simultaneas.
- **Fix:** Verificacion NLP tolerante a errores — si spaCy falla, la practica se registra igualmente con la oracion marcada como invalida.
- **Data:** Nueva columna `session_history.sentence_details` para perseguir el feedback de la oracion en la pagina de resultado.
- **Fix:** Conteo de practicas reconciliado (`SUM(times_practiced)` == registros en historial).

### v1.1 (2026-08-21)
- **Fix:** Validador NLP ahora soporta expresiones multi-palabra ("get lost", "show up on time", etc.) verificando tokens consecutivos en orden.
- **Fix:** Verbos auxiliares (is/are/was/were/be) ahora son aceptados como verbos validos en la verificacion de oraciones (POS: `AUX`).

### v1.0 (2026-08-20)
- Release inicial: quiz, spaced repetition SM-2, importacion Excel, CRUD de vocabulario, estadisticas.

---

## License

Distributed under the **MIT License**. See `LICENSE` for more information.

```
MIT License

Copyright (c) 2026 guillerdc006

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## Autor

**guillerdc006** — [GitHub](https://github.com/guillerdc006)
