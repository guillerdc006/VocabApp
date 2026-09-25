# Diccionario de Mediciones — VocabApp

Diccionario de referencia de **como se calcula cada metrica y cada visual** de VocabApp:
que mide, con que formula, de que datos se obtiene, donde se muestra y cual es su objetivo.
Tambien documenta el **objetivo de cada servicio** del sistema.

Sirve tanto para **leer los numeros de la app sin ambiguedad** (portfolio/analista)
como para **reimplementar el proyecto desde cero** (guia tecnica).

---

## Convenciones globales

- **UTC:** todos los timestamps (`created_at`, `next_review`, `last_practiced`) y los
  cortes de "hoy"/"dias" se calculan en **UTC** (`datetime.now(timezone.utc)`). SQLite los
  guarda como datetimes *naive* interpretados siempre como UTC. El sistema corre en
  `America/Guayaquil` (UTC-5); el dia UTC rueda a las 19:00 hora local.
- **Sesion vs practica:** una **sesion** es un registro de `session_history` (una oracion
  escrita en el quiz o una pareja completada en el matcher). Una **palabra practicada** es
  una palabra con `word_stats.times_practiced > 0`. No son lo mismo: en una practica de quiz
  se escriben varias sesiones/oraciones sobre la misma palabra.
- **Precision (definicion transversal):** `correctos / totales * 100`, redondeado a entero.
  El "correcto" que se cuenta es `is_correct` (mitad de palabra), a menos que se indique otra
  cosa (p. ej. "oraciones validas" usa `sentence_valid`).

---

## 1. Servicios y su objetivo

| Servicio | Archivo | Objetivo |
|---|---|---|
| SM-2 | `app/services/sm2.py` | Programar la proxima revision de cada palabra segun la calidad de la respuesta (Spaced Repetition). Funciones puras y testables: `sm2_review`, `get_next_review`, `determine_level`, `quality_from_score`. |
| Validacion de oraciones | `app/services/nlp_validator.py` | Juzgar si la oracion escrita por el usuario usa correctamente la palabra objetivo. Dos proveedores intercambiables con un mismo contrato de salida `{valid, word_found, has_verb, token_count, details, suggestion}`: **Gemini (IA)** cuando hay clave configurada y **spaCy (local)** como fallback automatico. Con **presupuesto de tiempo** garantizado (ver 3.4). |
| Importacion Excel | `app/services/excel_import.py` | Leer un `.xlsx` (columnas `english`/`spanish`/`observacion`) y crear/omitir palabras sin duplicar. |
| Analitica | `app/services/analytics.py` | Agregaciones puras sobre filas de historial/progreso para Estadisticas y Dashboard: precision diaria, heatmap de semanas, recalcular rachas, precision por dimension, skyline de repasos y ritmo diario. |
| Informe | `app/services/reporting.py` | Ensamblar **todas** las metricas en una sola pasada con **pandas** y renderizarlas con **matplotlib**: 5 graficos PNG incrustados en `/report` y un **PDF multipagina A4** (`/report/pdf`). Solo lectura de la BD. |

```text
Flujo de una practica de quiz:
  form del quiz → study_bp.quiz (POST)
      ├─ validate_answer()          → is_correct (mitad de palabra)
      ├─ validate_sentence_pipeline→ sentence_valid + details + validator_source
      │                              (Gemini con presupuesto → fallback spaCy)
      ├─ score = (palabra 50) + (oracion 50) + (bonus nivel 10, opcional)
      ├─ quality_from_score()       → quality SM-2 (0-5)
      ├─ sm2_review()               → repetitions, EF, interval
      ├─ determine_level()          → level (0-3)
      └─ v1.11 en adelante: sesion  → session_history (guardado con tudo)
            informar: analytics.py (estadisticas) + reporting.py (informe)
```

---

## 2. Datos fuente

### `words`
| Columna | Significado |
|---|---|
| `english` | Palabra/frase objetivo (UNIQUE) |
| `spanish` | Traduccion |
| `notes` | Observacion / pista (opcional, se muestra en el quiz) |
| `created_at` | Alta (UTC) |

### `word_stats` (1:1 con `words`)
| Columna | Significado |
|---|---|
| `repetitions` | # repeticiones consecutivas exitosas (SM-2) |
| `easiness_factor` | Factor de facilidad EF (SM-2, minimo 1.3) |
| `interval` | Intervalo actual en dias (SM-2) |
| `times_practiced` | # practicas de quiz registradas (debe ser igual al total de sesiones quiz de la palabra) |
| `times_correct` | # de esas practicas con la mitad de palabra correcta |
| `level` | Nivel SM-2: 0 Nueva, 1 Facil, 2 Media, 3 Dificil |
| `next_review` | Proxima fecha de repaso (UTC) |
| `last_practiced` | Ultima practica (UTC) |

### `session_history` (N:1 con `words`)
| Columna | Significado |
|---|---|
| `english_answer` | Lo que escribio el usuario (traduccion) |
| `sentence` | Oracion escrita |
| `sentence_details` | Feedback textual del validador |
| `sentence_suggestion` | Sugerencia de oracion corregida (solo Gemini) |
| `is_correct` | Mitad "palabra": traduccion correcta (0/1) |
| `sentence_valid` | Mitad "oracion": valida segun NLP (0/1) |
| `was_revealed` | 1 si se uso "No recuerdo / Ver respuesta" |
| `score` | Puntaje parcial (0-110) |
| `quality` | Calidad SM-2 (0-5) |
| `session_type` | `quiz` / `match` |
| `direction` | `es_to_en` / `en_to_es` / `match` |
| `validator_source` | `gemini` / `spacy` / `match` |
| `created_at` | Momento de la sesion (UTC) |

---

## 3. Diccionario de mediciones

### 3.1 Medidas basicas de una sesion de quiz

#### `is_correct` — mitad "palabra"
- **Que mide:** si la traduccion escrita coincide con la esperada.
- **Como se calcula:** `validate_answer(expected, user_answer)` — normaliza (minusculas,
  trim, espacios) y compara. Si se pulso el boton de ayuda, se fuerza `False` incluso si el
  texto coincide.
- **Fuente:** `words.english/spanish` (segun `direction`) + `session_history.is_correct`.
- **Donde:** resultado de practica, Estadisticas, informe.
- **Objetivo:** separar el conocimiento de la palabra del conocimiento de la oracion.
  Defiende al usuario de una practica de solo tipeo.

#### `sentence_valid` — mitad "oracion"
- **Que mide:** si la oracion usa la palabra objetivo correctamente.
- **Como se calcula:** pipeline NLP (3.4) sobre `word.english` y la oracion del usuario.
- **Fuente:** `session_history.sentence_valid`.
- **Objetivo:** fomentar el uso contextual, no solo la traduccion reconocida.

#### `score` — puntaje parcial (0-110)
- **Que mide:** rendimiento de la practica en dos componentes.
- **Como se calcula:**
  ```
  score = 50 (palabra correcta) + 50 (oracion valida) + 10 de bonus
  10 de bonus = nivel 3 y palabra correcta (bonus por consolidar lo dificil)
  ```
- **Nota:** no es lo mismo que `quality`; es la calificacion mostrada al usuario.
- **Fuente:** `session_history.score`.

#### `quality` — calidad SM-2 (0-5)
- **Que mide:** la calidad que alimenta al algoritmo SM-2.
- **Como se calcula** (`quality_from_score`, `sm2.py:43`):
  ```
  5 = palabra correcta + oracion valida
  4 = palabra correcta + oracion invalida
  3 = palabra incorrecta + oracion valida
  1 = ambas incorrectas
  ```
- **Fuente:** `session_history.quality`.

#### `was_revealed` — practica con ayuda
- **Que mide:** si la respuesta se revelo con "No recuerdo / Ver respuesta".
- **Como se calcula:** `1` si el usuario pulso el boton; eso fuerza `is_correct=False`
  (la palabra se marca como fallo SM-2, `quality` nunca puede ser 4-5 por esa sesion).
- **Fuente:** `session_history.was_revealed`.
- **Objetivo:** registrar honestamente la ayuda y detectar sesgo de reporte (ver 5).

### 3.2 Dashboard (`/`)

| Metrica | Que mide | Como se calcula | Fuente |
|---|---|---|---|
| Total de palabras | Vocabulario cargado | `COUNT(words)` | `words` |
| Palabras practicadas | Palabras distintas con al menos 1 practica | `COUNT(word_stats WHERE times_practiced > 0)` | `word_stats` |
| Oraciones practicadas | Total de sesiones registradas | `COUNT(session_history)` | `session_history` |
| Pendientes para practica | Palabras nunca repasadas | `COUNT(word_stats WHERE next_review IS NULL)` | `word_stats` |
| Precision (ult. 7 dias) | Aciertos de palabra en la ultima semana | `correctos / sesiones >= now-7d * 100` | `session_history` |
| Niveles (0-3) | Distribucion de dificultad | `GROUP BY level` | `word_stats` |
| Nuevas pendientes / Vencidas / Cola | Carga SM-2 de hoy | ver 3.3 | `word_stats` |

- **Objetivo:** una mirada de 5 segundos al estado de salud del repaso.

### 3.3 Carga de repaso (SM-2)

Metricas clave para la sostenibilidad del repaso (`study_bp.stats`, `main_bp.index`):

| Metrica | Que mide | Como se calcula | Fuente |
|---|---|---|---|
| Nuevas pendientes | Palabras nunca repasadas, sin `next_review` | `COUNT(next_review IS NULL)` | `word_stats` |
| Vencidas (hoy + atrasadas) | Repasos que ya tocan | `next_review < end_today` (inicio del dia UTC de hoy + 1) | `word_stats` |
| Cola total | Todo lo que hay que atender | `nuevas + vencidas` | `word_stats` |
| Practicadas hoy | Palabras distintas ejercitadas en el dia UTC | `COUNT(DISTINCT word_id WHERE created_at >= inicio de hoy)` | `session_history` |
| Ritmo diario | Palabras distintas por dia (ventana 7 dias) | `daily_practice_rate()` (3.2 analitica) | `session_history` |
| Dias para despejar | Proyeccion simple | `ceil(cola / ritmo_diario)` si ritmo > 0 | derivada |
| Repasos programados (14 dias) | Dependencia futura | `review_skyline()`: conteo de `next_review` por dia desde manana | `word_stats` |
| Aviso de ritmo | ¿La deuda supera la capacidad? | `vencidas > sum(ritmo 7 dias)` → "Considera aumentar la practica" | derivada |

- **Objetivo:** el mismo diagnostico de backlog que haria un CRM: si las vencidas superan lo
  que se despeja por semana, la cola crece inevitablemente.

### 3.4 Validacion de oraciones (NLP)

- **Que mide:** calidad formal de la oracion y uso correcto de la palabra.
- **Como se calcula** (`nlp_validator.py`):
  1. Se elige proveedor: **Gemini** si hay `GEMINI_API_KEY` y `NLP_VALIDATOR=gemini`;
     si falla, tarda (presupuesto) o no esta configurado → **spaCy**.
  2. **Presupuesto (`GEMINI_TIMEOUT_MS`):** la llamada corre en un hilo con
     `future.result(timeout=presupuesto)`. El deadline HTTP por intento esta fijo en
     `10000 ms` (minimo que exige la API); el corte de UX lo pone el presupuesto
     (default `3000 ms`). Peor caso de espera = presupuesto; tipico < 1 s.
  3. **spaCy (verificaciones):** la palabra/expresion presente con tokens consecutivos
     en orden (soporta inflexiones y expresiones multi-palabra como "get lost");
     al menos un verbo (`VERB` o `AUX`); 3+ tokens sin puntuacion.
  4. **Gemini** ademas juzga uso real (palabra con inflexiones: go → went/gone) y devuelve
     una **sugerencia** de oracion corregida cuando falla.
- **Salida:** contrato uniforme `{valid, word_found, has_verb, token_count, details, suggestion}`
  + `validator_source` (`gemini`/`spacy`) que se guarda por sesion.
- **Objetivo:** corregir la oracion, no castigar: una oracion invalida no invalida la
  traduccion correcta (quality 4). El tag `validator_source` permite medir la precision
  separando el factor "palabra dificil" del factor "evaluador".

### 3.5 Estadisticas (`/study/stats`)

| Metrica | Que mide | Como se calcula | Fuente |
|---|---|---|---|
| Precision general (historica) | Aciertos de palabra sobre todas las practicas acumuladas | `SUM(times_correct)/SUM(times_practiced)*100` | `word_stats` |
| Precisión por tipo | Quiz vs Matcher | `accuracy_by_dimension(session_type, is_correct)` | `session_history` |
| Precision por direccion | `es_to_en` vs `en_to_es` | `accuracy_by_dimension(direction, is_correct)` | `session_history` |
| Precision por validador | Gemini vs spaCy (solo sesiones avec validador) | `accuracy_by_dimension(validator_source, is_correct)` filtrando `gemini`/`spacy` | `session_history` |
| Practicas con ayuda | Pulsaciones del boton de ayuda | `COUNT(was_revealed = True)` | `session_history` |
| Racha actual | Dias consecutivos con practica (anclada a hoy o ayer) | `compute_streaks()`: si hoy no tiene practica aun, se ancla a ayer; si no hay practica desde hace 2+ dias → 0 | `session_history.created_at` |
| Mejor racha | Record historico | Maximo run de dias consecutivos | `session_history.created_at` |
| Dias activos | Dias distintos con al menos una sesion | `COUNT(DISTINCT date(created_at))` | derivada |
| Evolucion 30 dias | Precision diaria por tipo | `daily_accuracy_by_type()`: `correctos/sesiones` del dia (UTC); cada tipo solo se dibuja si tuvo actividad | `session_history` |
| Calendario de actividad | Intensidad diaria (heatmap de 16 semanas) | `activity_weeks()`: sesiones por dia; `level = 0..4` = `min(count, 4)` (cap visual) | `session_history.created_at` |
| Mas dificiles / mejor dominadas | Top 10 por rendimiento | dificiles: `falas = times_practiced - times_correct` (mayor); mejor: `times_correct` (mayor) | `word_stats` |
| Historial paginado | Log completo con filtros (palabra, resultado, tipo, fechas) | 20 por pagina | `session_history` + `words` |

### 3.6 Informe (`/report` y `/report/pdf`)

Una sola pasada de datos (`build_report_data()`, `reporting.py`) alimenta **todas** las
metricas (+ las de 3.3/3.5), de forma reproducible (marca UTC de generacion):

| Visual | Que muestra | Como se calcula |
|---|---|---|
| Tarjetas de numeros | Palabras totales, practicadas, precision general, sesiones, precision quiz, % oraciones validas, puntaje promedio, practicas con ayuda, racha actual/mejor, cola, practicadas hoy | agregaciones de 3.2/3.3/3.5 |
| Grafico 1 — Precision por tipo, direccion y validador | 3 pares de barras (0-100%) | `accuracy_by_dimension` + `by_validator` |
| Grafico 2 — Evolucion de precision (30 dias) | Linea por tipo (quiz/match), solapadas | `daily_accuracy_by_type()` |
| Grafico 3 — Calendario de actividad (16 semanas) | Heatmap de practicas | `activity_weeks()` |
| Grafico 4 — Distribucion por nivel SM-2 | Barras horizontales (Nueva/Facil/Media/Dificil) | `level_counts` |
| Grafico 5 — Carga de repaso programada (14 dias) | Area de repasos futuros | `review_skyline()` |
| Tablas — Mas dificiles / Mejor dominadas | Top 10 con % precision, fallos, veces | `word_list()` |

- **Objetivo del servicio `reporting`:** convertir datos crudos en **decisiones de estudio**
  (ver seccion "Estudio de caso" del README). Es una capa de solo lectura sobre la BD,
  pensada para correr en servidor (matplotlib backend `Agg`, sin ventanas).

---

## 4. Niveles SM-2 (definicion de `determine_level`)

| Nivel | Nombre | Regla |
|---|---|---|
| 0 | Nueva | estado inicial (nunca practicada) |
| 1 | Facil | `repetitions >= 3` y `EF >= 2.5`; o rutas de consolidacion |
| 2 | Media | `repetitions <= 2` o `EF < 2.0` (sin caer en dificil) |
| 3 | Dificil | algun fallo reciente (`quality < 3`) o `EF < 1.8` |

Un fallo (`quality < 3`) **reinicia repetitions a 0** e intervalo a 1 dia (SM-2 puro).
El nivel del matcher no cambia la curva; solo el quiz lo hace.

---

## 5. Consideraciones de interpretacion (analista)

1. **Sesgo del boton de ayuda:** sin `was_revealed`, la precision real seria optimista.
   Con el registro, puedes medir cuantas palabras resuelves sin esfuerzo y detectar si el
   boton se convierte en atajo (revisar el contador "Practicas con ayuda" del informe).
2. **Sesgo del evaluador:** la precision por validador separa la dificultad real de la
   palabra del ruido del evaluador. Las sesiones validadas con spaCy pueden rechazar
   oraciones correctas (reglas heuristicas) que Gemini aceptaria — no es un fallo tuyo.
3. **Tiempo en UTC:** "hoy" es consistente pase lo que pase la hora local; el informe lleva
   su marca UTC para que una captura sea reproducible.
4. **Matcher vs Quiz:** el matcher alimenta precision por tipo y actividad, pero **no** toca
   `next_review`/niveles: solo el quiz avanza la curva SM-2.
5. **Ventana de 7 dias del dashboard** vs **30 dias de la evolucion**: no compiten, son
   perspectivas (salud semanal vs tendencia mensual).