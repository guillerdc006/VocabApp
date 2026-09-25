from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime, timezone, timedelta
import json
import random
from ..models import Word, WordStats, SessionHistory
from ..extensions import db
from ..services.sm2 import sm2_review, get_next_review, determine_level, quality_from_score
from ..services.nlp_validator import validate_answer, validate_sentence_pipeline
from ..services.analytics import (
    compute_streaks,
    accuracy_by_dimension,
    daily_accuracy_by_type,
    activity_weeks,
    review_skyline,
    daily_practice_rate,
)

study_bp = Blueprint("study", __name__)

VALID_DIRECTIONS = {"es_to_en", "en_to_es"}


def _normalize_direction(value):
    return value if value in VALID_DIRECTIONS else "es_to_en"


def get_quiz_word():
    now = datetime.now(timezone.utc)

    pending = (
        db.session.query(Word)
        .join(WordStats)
        .filter(WordStats.next_review.is_(None))
        .all()
    )
    if pending:
        return random.choice(pending)

    due = (
        db.session.query(Word)
        .join(WordStats)
        .filter(
            WordStats.next_review.isnot(None),
            WordStats.next_review <= now,
        )
        .all()
    )
    if due:
        return random.choice(due)

    all_words = Word.query.all()
    if all_words:
        return random.choice(all_words)
    return None


@study_bp.route("/quiz", methods=["GET", "POST"])
def quiz():
    if request.method == "POST":
        direction = _normalize_direction(request.form.get("direction"))
        session["quiz_direction"] = direction

        word_id = request.form.get("word_id", type=int)
        user_answer = request.form.get("english_answer", "").strip()
        user_sentence = request.form.get("sentence", "").strip()
        was_revealed = request.form.get("revealed") == "1"

        word = Word.query.get_or_404(word_id)
        stats = WordStats.query.filter_by(word_id=word_id).first()
        if not stats:
            stats = WordStats(word_id=word_id)
            db.session.add(stats)

        expected = word.spanish if direction == "en_to_es" else word.english
        is_correct = validate_answer(expected, user_answer)
        if was_revealed:
            is_correct = False
        try:
            sentence_result, validator_source = validate_sentence_pipeline(word.english, user_sentence)
        except Exception:
            sentence_result = {"valid": False, "details": "No se pudo verificar la oracion (error NLP)"}
            validator_source = "spacy"

        score = 0
        if is_correct:
            score += 50
        if sentence_result["valid"]:
            score += 50
        if stats.level == 3 and is_correct:
            score += 10

        quality = quality_from_score(is_correct, sentence_result["valid"], score)
        new_rep, new_ef, new_interval = sm2_review(
            stats.repetitions, stats.easiness_factor, stats.interval, quality
        )

        stats.repetitions = new_rep
        stats.easiness_factor = new_ef
        stats.interval = new_interval
        stats.times_practiced += 1
        if is_correct:
            stats.times_correct += 1
        stats.level = determine_level(new_rep, new_ef, quality)
        stats.next_review = get_next_review(new_interval)
        stats.last_practiced = datetime.now(timezone.utc)

        history = SessionHistory(
            word_id=word_id,
            english_answer=user_answer,
            sentence=user_sentence,
            sentence_details=sentence_result["details"],
            is_correct=is_correct,
            sentence_valid=sentence_result["valid"],
            score=score,
            quality=quality,
            session_type="quiz",
            direction=direction,
            validator_source=validator_source,
            sentence_suggestion=sentence_result.get("suggestion"),
            was_revealed=was_revealed,
        )
        db.session.add(history)
        db.session.commit()

        return redirect(url_for("study.result", history_id=history.id))

    direction = _normalize_direction(request.args.get("direction") or session.get("quiz_direction"))
    session["quiz_direction"] = direction

    word = get_quiz_word()
    if not word:
        flash("No hay palabras en la base de datos. Agrega vocabulario primero.", "warning")
        return redirect(url_for("vocabulary.word_list"))

    stats = WordStats.query.filter_by(word_id=word.id).first()
    expected_answer = word.spanish if direction == "en_to_es" else word.english
    return render_template(
        "study/quiz.html", word=word, stats=stats, direction=direction, expected_answer=expected_answer
    )


@study_bp.route("/result/<int:history_id>")
def result(history_id):
    history = SessionHistory.query.get_or_404(history_id)
    word = Word.query.get_or_404(history.word_id)

    sentence_result = {
        "valid": history.sentence_valid,
        "details": history.sentence_details or ("Oracion valida. La palabra esta correctamente utilizada." if history.sentence_valid else "Oracion no validada"),
    }

    return render_template(
        "study/result.html",
        word=word,
        user_answer=history.english_answer,
        user_sentence=history.sentence,
        is_correct=history.is_correct,
        sentence_result=sentence_result,
        score=history.score,
        quality=history.quality,
        direction=history.direction,
        validator_source=history.validator_source,
        sentence_suggestion=history.sentence_suggestion,
        was_revealed=history.was_revealed,
    )


@study_bp.route("/match")
def match():
    available = db.session.query(Word).join(WordStats).all()
    words = random.sample(available, k=min(10, len(available)))
    left = random.sample(words, k=len(words))
    right = random.sample(words, k=len(words))
    return render_template("study/match.html", left=left, right=right)


@study_bp.route("/match/complete", methods=["POST"])
def match_complete():
    raw = request.form.get("ids", "")
    try:
        payload = json.loads(raw) if raw else {}
    except (json.JSONDecodeError, TypeError):
        payload = {}
    ids = payload.get("ids", [])
    valid_ids = [i for i in ids if isinstance(i, int)]
    if not valid_ids:
        flash("No se registraron parejas completadas.", "warning")
        return redirect(url_for("study.match"))

    words = db.session.query(Word).filter(Word.id.in_(valid_ids)).all()
    for w in words:
        db.session.add(
            SessionHistory(
                word_id=w.id,
                english_answer=w.english,
                sentence_valid=True,
                is_correct=True,
                score=100,
                quality=5,
                session_type="match",
                direction="match",
                validator_source="match",
            )
        )
    db.session.commit()
    flash(f"Matcher completado: {len(words)} parejas de {len(valid_ids)}.", "success")
    return redirect(url_for("study.match"))


@study_bp.route("/stats")
def stats():
    total_words = Word.query.count()
    total_practiced = WordStats.query.filter(WordStats.times_practiced > 0).count()
    total_correct = db.session.query(db.func.sum(WordStats.times_correct)).scalar() or 0
    total_practices = db.session.query(db.func.sum(WordStats.times_practiced)).scalar() or 0

    overall_accuracy = 0
    if total_practices > 0:
        overall_accuracy = round(total_correct / total_practices * 100)

    activity_days = {
        row[0].date()
        for row in db.session.query(SessionHistory.created_at).all()
    }
    current_streak, best_streak = compute_streaks(activity_days)

    dimension_rows = db.session.query(
        SessionHistory.session_type,
        SessionHistory.direction,
        SessionHistory.is_correct,
    ).all()
    accuracy_by_type = accuracy_by_dimension(
        (r.session_type, r.is_correct) for r in dimension_rows
    )
    accuracy_by_direction = accuracy_by_dimension(
        (r.direction, r.is_correct) for r in dimension_rows
    )
    validator_rows = (
        db.session.query(
            SessionHistory.validator_source, SessionHistory.is_correct
        )
        .filter(SessionHistory.validator_source.in_(["gemini", "spacy"]))
        .all()
    )
    accuracy_by_validator = accuracy_by_dimension(
        (v, ok) for v, ok in validator_rows
    )
    validator_counts = {}
    for v, ok in validator_rows:
        validator_counts[v] = validator_counts.get(v, 0) + 1

    evolution = daily_accuracy_by_type(
        db.session.query(
            SessionHistory.created_at,
            SessionHistory.is_correct,
            SessionHistory.session_type,
        ).all()
    )
    weeks = activity_weeks(
        (row[0] for row in db.session.query(SessionHistory.created_at).all())
    )

    now = datetime.now(timezone.utc)
    start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_today = start_today + timedelta(days=1)

    new_pending = (
        WordStats.query.filter(WordStats.next_review.is_(None)).count()
    )
    vencidas_total = (
        WordStats.query.filter(
            WordStats.next_review.isnot(None), WordStats.next_review < end_today
        ).count()
    )
    backlog = new_pending + vencidas_total

    practiced_today = (
        db.session.query(db.func.count(db.func.distinct(SessionHistory.word_id)))
        .filter(SessionHistory.created_at >= start_today)
        .scalar()
        or 0
    )
    practices_with_help = db.session.query(
        db.func.count(SessionHistory.id)
    ).filter(SessionHistory.was_revealed == True).scalar() or 0
    backlog_ayer = backlog + practiced_today

    rate_series = daily_practice_rate(
        db.session.query(SessionHistory.created_at, SessionHistory.word_id).all()
    )
    rate_avg = round(sum(d["count"] for d in rate_series) / len(rate_series)) if rate_series else 0
    days_to_clear = (
        (backlog + rate_avg - 1) // rate_avg if rate_avg > 0 and backlog > 0 else None
    )
    skyline = review_skyline(
        (row[0] for row in db.session.query(WordStats.next_review).filter(WordStats.next_review.isnot(None)).all())
    )

    weekly_cleared = sum(d["count"] for d in rate_series)
    need_more = vencidas_total > weekly_cleared

    prompt = (
        "Considera aumentar la practica: las vencidas acumuladas ya superan lo que despejas por semana."
        if need_more
        else "Buen ritmo: la cola pendiente esta bajo control."
    )

    hardest_words = (
        db.session.query(Word, WordStats)
        .join(WordStats)
        .filter(WordStats.times_practiced > 0)
        .order_by(WordStats.times_practiced - WordStats.times_correct.desc())
        .limit(10)
        .all()
    )

    easiest_words = (
        db.session.query(Word, WordStats)
        .join(WordStats)
        .filter(WordStats.times_practiced > 0)
        .order_by(WordStats.times_correct.desc())
        .limit(10)
        .all()
    )

    recent_query = db.session.query(SessionHistory, Word).join(Word)

    word_filter = request.args.get("word", "").strip()
    correct_filter = request.args.get("correct", "").strip()
    session_type_filter = request.args.get("session_type", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    if word_filter:
        recent_query = recent_query.filter(
            db.or_(
                Word.english.ilike(f"%{word_filter}%"),
                Word.spanish.ilike(f"%{word_filter}%"),
            )
        )
    if correct_filter == "yes":
        recent_query = recent_query.filter(SessionHistory.is_correct == True)
    elif correct_filter == "no":
        recent_query = recent_query.filter(SessionHistory.is_correct == False)
    if session_type_filter in ("quiz", "match"):
        recent_query = recent_query.filter(
            SessionHistory.session_type == session_type_filter
        )
    if date_from:
        try:
            recent_query = recent_query.filter(
                SessionHistory.created_at
                >= datetime.strptime(date_from, "%Y-%m-%d")
            )
        except ValueError:
            date_from = ""
    if date_to:
        try:
            recent_query = recent_query.filter(
                SessionHistory.created_at
                < datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
            )
        except ValueError:
            date_to = ""

    page = request.args.get("page", 1, type=int)
    pagination = recent_query.order_by(SessionHistory.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    filter_params = {
        k: v for k, v in request.args.items() if k != "page" and v
    }

    return render_template(
        "study/stats.html",
        total_words=total_words,
        total_practiced=total_practiced,
        overall_accuracy=overall_accuracy,
        active_days=len(activity_days),
        current_streak=current_streak,
        best_streak=best_streak,
        accuracy_by_type=accuracy_by_type,
        accuracy_by_direction=accuracy_by_direction,
        accuracy_by_validator=accuracy_by_validator,
        validator_counts=validator_counts,
        evolution=evolution,
        weeks=weeks,
        new_pending=new_pending,
        vencidas_total=vencidas_total,
        backlog=backlog,
        backlog_ayer=backlog_ayer,
        practiced_today=practiced_today,
        practices_with_help=practices_with_help,
        rate_avg=rate_avg,
        days_to_clear=days_to_clear,
        skyline=skyline,
        rate_series=rate_series,
        need_more=need_more,
        prompt=prompt,
        hardest_words=hardest_words,
        easiest_words=easiest_words,
        pagination=pagination,
        word=word_filter,
        correct=correct_filter,
        session_type=session_type_filter,
        date_from=date_from,
        date_to=date_to,
        filter_params=filter_params,
    )
