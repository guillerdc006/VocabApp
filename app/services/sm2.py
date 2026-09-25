from datetime import datetime, timedelta, timezone
import math


def sm2_review(repetitions, easiness_factor, interval, quality):
    if quality < 0 or quality > 5:
        raise ValueError("Quality must be between 0 and 5")

    new_ef = easiness_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_ef = max(1.3, new_ef)

    if quality < 3:
        new_repetitions = 0
        new_interval = 1
    else:
        new_repetitions = repetitions + 1
        if new_repetitions == 1:
            new_interval = 1
        elif new_repetitions == 2:
            new_interval = 6
        else:
            new_interval = math.ceil(interval * new_ef)

    return new_repetitions, new_ef, new_interval


def get_next_review(interval):
    return datetime.now(timezone.utc) + timedelta(days=interval)


def determine_level(repetitions, easiness_factor, quality):
    if quality < 3:
        return 3
    if repetitions >= 3 and easiness_factor >= 2.5:
        return 1
    if easiness_factor < 1.8:
        return 3
    if repetitions <= 2 or easiness_factor < 2.0:
        return 2
    return 1


def quality_from_score(is_correct, sentence_valid, score):
    if is_correct and sentence_valid:
        return 5
    if is_correct and not sentence_valid:
        return 4
    if not is_correct and sentence_valid:
        return 3
    return 1
