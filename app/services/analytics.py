from datetime import datetime, timedelta, timezone
from collections import defaultdict


def daily_accuracy(rows, window_days=30):
    """Accuracy per UTC day for the last `window_days` days.

    rows: iterable of (created_at, is_correct).
    Returns one dict per day (ordered): label ISO, accuracy pct or None if the
    day has no practice, and total sessions.
    """
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=window_days - 1)
    days = {start + timedelta(days=i): [0, 0] for i in range(window_days)}
    for created_at, ok in rows:
        d = created_at.date()
        if d in days:
            days[d][1] += 1
            if ok:
                days[d][0] += 1
    return [
        {
            "label": d.isoformat(),
            "accuracy": round(days[d][0] / days[d][1] * 100) if days[d][1] else None,
            "total": days[d][1],
        }
        for d in sorted(days)
    ]


def activity_weeks(rows, weeks=16):
    """Heatmap grid of weeks x days, ending on the current UTC week.

    rows: iterable of created_at datetimes.
    Returns `weeks` week lists, each with 7 day dicts:
    {iso, count, level (0..4), future}.
    """
    today = datetime.now(timezone.utc).date()
    monday = today - timedelta(days=today.weekday())
    start = monday - timedelta(weeks=weeks - 1)
    counts = defaultdict(int)
    for created_at in rows:
        d = created_at.date()
        if start <= d <= today:
            counts[d] += 1
    result = []
    for w in range(weeks):
        week_start = start + timedelta(weeks=w)
        week = []
        for i in range(7):
            d = week_start + timedelta(days=i)
            c = counts.get(d, 0)
            week.append(
                {
                    "iso": d.isoformat(),
                    "count": c,
                    "level": 0 if c == 0 else min(c, 4),
                    "future": d > today,
                }
            )
        result.append(week)
    return result


def daily_accuracy_by_type(rows, window_days=30):
    """Accuracy per UTC day split by session_type (quiz/match).

    rows: iterable of (created_at, is_correct, session_type).
    Returns {"quiz": [day dicts], "match": [day dicts]} with one entry per day
    in the window (accuracy None if that type had no practice that day).
    """
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=window_days - 1)
    day_index = {start + timedelta(days=i): i for i in range(window_days)}
    series = {
        "quiz": {i: [0, 0] for i in range(window_days)},
        "match": {i: [0, 0] for i in range(window_days)},
    }
    for created_at, ok, stype in rows:
        idx = day_index.get(created_at.date()) if stype in series else None
        if idx is None:
            continue
        series[stype][idx][1] += 1
        if ok:
            series[stype][idx][0] += 1
    result = {}
    for stype, data in series.items():
        result[stype] = [
            {
                "label": (start + timedelta(days=i)).isoformat(),
                "accuracy": round(data[i][0] / data[i][1] * 100) if data[i][1] else None,
                "total": data[i][1],
            }
            for i in range(window_days)
        ]
    return result


def review_skyline(rows, days=14):
    """Scheduled reviews per day for the next `days` days (tomorrow included).

    rows: iterable of next_review datetimes.
    Returns ordered list of {"label": ISO, "count": scheduled count}.
    """
    today = datetime.now(timezone.utc).date()
    start_day = today + timedelta(days=1)
    counts = defaultdict(int)
    for dt in rows:
        d = dt.date() if isinstance(dt, datetime) else dt
        if start_day <= d <= start_day + timedelta(days=days - 1):
            counts[d] += 1
    return [
        {
            "label": (start_day + timedelta(days=i)).isoformat(),
            "count": counts.get(start_day + timedelta(days=i), 0),
        }
        for i in range(days)
    ]


def daily_practice_rate(rows, days=7):
    """Distinct words practiced per UTC day for the last `days` days.

    rows: iterable of (created_at, word_id).
    Returns ordered list of {"label": ISO, "count": distinct words}.
    """
    today = datetime.now(timezone.utc).date()
    start_day = today - timedelta(days=days - 1)
    practiced = defaultdict(set)
    for created_at, word_id in rows:
        d = created_at.date()
        if start_day <= d <= today:
            practiced[d].add(word_id)
    return [
        {
            "label": (start_day + timedelta(days=i)).isoformat(),
            "count": len(practiced.get(start_day + timedelta(days=i), set())),
        }
        for i in range(days)
    ]


def compute_streaks(days):
    """Return (current_streak, best_streak) given an iterable of dates.

    A streak counts consecutive days with practice. The current streak
    anchors on today, or on yesterday if today has no practice yet.
    Days are treated in UTC (the timezone used to store practice dates).
    """
    dset = set(days)
    if not dset:
        return 0, 0

    ordered = sorted(dset)
    best = 1
    run = 1
    for a, b in zip(ordered, ordered[1:]):
        if (b - a).days == 1:
            run += 1
        else:
            best = max(best, run)
            run = 1
    best = max(best, run)

    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)
    if today in dset:
        anchor = today
    elif yesterday in dset:
        anchor = yesterday
    else:
        return 0, best

    current = 1
    d = anchor - timedelta(days=1)
    while d in dset:
        current += 1
        d -= timedelta(days=1)

    return current, best


def accuracy_by_dimension(rows):
    """Aggregate (dimension, is_correct) rows into {dimension: accuracy_pct}."""
    totals = {}
    correct = {}
    for dimension, ok in rows:
        totals[dimension] = totals.get(dimension, 0) + 1
        if ok:
            correct[dimension] = correct.get(dimension, 0) + 1
    return {
        dimension: int(round(correct.get(dimension, 0) / total * 100))
        for dimension, total in totals.items()
    }