from flask import Blueprint, render_template
from ..models import Word, WordStats, SessionHistory
from ..extensions import db
from datetime import datetime, timezone, timedelta

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    total_words = Word.query.count()
    practiced_words = WordStats.query.filter(WordStats.times_practiced > 0).count()
    total_sessions = SessionHistory.query.count()
    pending_count = WordStats.query.filter(WordStats.next_review.is_(None)).count()

    now = datetime.now(timezone.utc)
    start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_today = start_today + timedelta(days=1)
    new_pending = WordStats.query.filter(WordStats.next_review.is_(None)).count()
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

    week_ago = now - timedelta(days=7)
    recent_sessions = SessionHistory.query.filter(
        SessionHistory.created_at >= week_ago
    ).count()

    recent_correct = SessionHistory.query.filter(
        SessionHistory.created_at >= week_ago,
        SessionHistory.is_correct == True,
    ).count()

    accuracy_week = 0
    if recent_sessions > 0:
        accuracy_week = round(recent_correct / recent_sessions * 100)

    level_counts = db.session.query(
        WordStats.level, db.func.count(WordStats.id)
    ).group_by(WordStats.level).all()
    levels = {0: 0, 1: 0, 2: 0, 3: 0}
    for level, count in level_counts:
        levels[level] = count

    return render_template(
        "main/index.html",
        total_words=total_words,
        practiced_words=practiced_words,
        total_sessions=total_sessions,
        pending_count=pending_count,
        recent_sessions=recent_sessions,
        accuracy_week=accuracy_week,
        levels=levels,
        new_pending_short=new_pending,
        vencidas_total=vencidas_total,
        backlog=backlog,
        practiced_today=practiced_today,
    )
