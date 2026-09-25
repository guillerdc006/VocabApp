import base64
import io
from datetime import datetime, timezone, timedelta

import matplotlib

matplotlib.use("Agg")  # sin ventanas (servidor)

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

from ..extensions import db
from ..models import SessionHistory, Word, WordStats
from .analytics import (
    activity_weeks,
    compute_streaks,
    daily_accuracy_by_type,
    daily_practice_rate,
    review_skyline,
)

_LEVEL_NAMES = {0: "Nueva", 1: "Facil", 2: "Media", 3: "Dificil"}
_LEVEL_COLORS = ["#6b7280", "#22c55e", "#eab308", "#ef4444"]

_HISTORY_COLUMNS = [
    "created_at",
    "word_id",
    "is_correct",
    "session_type",
    "direction",
    "validator_source",
    "was_revealed",
    "sentence_valid",
    "score",
    "quality",
]


def build_report_data():
    """Todas las metricas del informe, ensambladas con pandas (solo lectura)."""
    now = datetime.now(timezone.utc)
    hist_rows = db.session.query(
        SessionHistory.created_at,
        SessionHistory.word_id,
        SessionHistory.is_correct,
        SessionHistory.session_type,
        SessionHistory.direction,
        SessionHistory.validator_source,
        SessionHistory.was_revealed,
        SessionHistory.sentence_valid,
        SessionHistory.score,
        SessionHistory.quality,
    ).all()
    hist = pd.DataFrame(hist_rows, columns=_HISTORY_COLUMNS)

    stats_rows = db.session.query(
        WordStats.word_id,
        WordStats.times_practiced,
        WordStats.times_correct,
        WordStats.level,
        WordStats.next_review,
    ).all()
    stats_df = pd.DataFrame(
        stats_rows,
        columns=["word_id", "times_practiced", "times_correct", "level", "next_review"],
    )

    n_words = Word.query.count()
    practiced = stats_df[stats_df["times_practiced"] > 0] if not stats_df.empty else stats_df
    n_practiced = len(practiced)
    total_practices = int(stats_df["times_practiced"].sum())
    total_correct = int(stats_df["times_correct"].sum())
    all_time_accuracy = (
        round(total_correct / total_practices * 100) if total_practices else 0
    )

    n_sessions = len(hist)
    helped = int((hist["was_revealed"] == True).sum()) if n_sessions else 0
    quiz = hist[hist["session_type"] == "quiz"] if n_sessions else hist
    quiz_sessions = len(quiz)
    quiz_correct = int(quiz["is_correct"].sum()) if quiz_sessions else 0
    quiz_accuracy = round(quiz_correct / quiz_sessions * 100) if quiz_sessions else 0
    valid_sentence_rate = (
        round(int(quiz["sentence_valid"].sum()) / quiz_sessions * 100) if quiz_sessions else 0
    )
    avg_score = int(round(hist["score"].mean())) if n_sessions else 0
    avg_quality = round(float(hist["quality"].mean()), 1) if n_sessions else 0.0

    activity_days = set(hist["created_at"].dt.date) if n_sessions else set()
    current_streak, best_streak = compute_streaks(activity_days)

    def accuracy_by(keys, values):
        if len(keys) == 0:
            return {}
        g = pd.DataFrame({"k": keys, "ok": values}).groupby("k")["ok"].agg(
            ["sum", "count"]
        )
        return {
            str(k): int(round(r["sum"] / r["count"] * 100)) for k, r in g.iterrows()
        }

    by_type = accuracy_by(hist["session_type"], hist["is_correct"])
    by_direction = accuracy_by(hist["direction"], hist["is_correct"])
    val_mask = hist["validator_source"].isin(["gemini", "spacy"]) if n_sessions else pd.Series([], dtype=bool)
    by_validator = accuracy_by(
        hist.loc[val_mask, "validator_source"], hist.loc[val_mask, "is_correct"]
    )
    validator_counts = (
        hist.loc[val_mask, "validator_source"].value_counts().to_dict()
        if n_sessions
        else {}
    )

    level_counts = stats_df["level"].value_counts() if not stats_df.empty else pd.Series(dtype=int)
    level_dist = [
        {"level": i, "name": _LEVEL_NAMES.get(i, "Nueva"), "count": int(level_counts.get(i, 0))}
        for i in range(4)
    ]

    start_today = now.replace(hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)
    end_today = start_today + timedelta(days=1)
    new_pending = int(stats_df["next_review"].isna().sum())
    due_mask = stats_df["next_review"].notna() & (pd.to_datetime(stats_df["next_review"]) < end_today)
    vencidas_total = int(due_mask.sum())
    backlog = new_pending + vencidas_total
    practiced_today = (
        len(hist[hist["created_at"] >= start_today]["word_id"].unique()) if n_sessions else 0
    )

    word_map = {w.id: w for w in Word.query.all()}

    def word_list(df, sort_by, ascending):
        out = []
        for r in df.sort_values(sort_by, ascending=ascending).head(10).itertuples():
            w = word_map.get(int(r.word_id))
            if w is None:
                continue
            tp = int(r.times_practiced)
            out.append(
                {
                    "english": w.english,
                    "spanish": w.spanish,
                    "times_practiced": tp,
                    "accuracy": round(int(r.times_correct) / tp * 100) if tp else 0,
                    "failures": tp - int(r.times_correct),
                }
            )
        return out

    practiced_df = practiced[["word_id", "times_practiced", "times_correct"]]
    practiced_df["failures"] = practiced_df["times_practiced"] - practiced_df["times_correct"]
    hardest = word_list(practiced_df, ["failures", "times_practiced"], [False, False])
    easiest = word_list(
        practiced_df[["word_id", "times_practiced", "times_correct"]],
        ["times_correct", "times_practiced"],
        [False, True],
    )

    skyline = review_skyline(
        row for row in stats_df["next_review"].dropna()
    )
    weeks = activity_weeks((row for row in hist["created_at"])) if n_sessions else activity_weeks([])
    evolution = daily_accuracy_by_type(
        ((c, ok, st) for c, ok, st in zip(hist["created_at"], hist["is_correct"], hist["session_type"]))
    )
    rate = daily_practice_rate(
        ((c, wid) for c, wid in zip(hist["created_at"], hist["word_id"]))
    )
    rate_avg = round(sum(d["count"] for d in rate) / len(rate)) if rate else 0

    return {
        "n_words": n_words,
        "n_practiced": n_practiced,
        "all_time_accuracy": all_time_accuracy,
        "n_sessions": n_sessions,
        "quiz_accuracy": quiz_accuracy,
        "valid_sentence_rate": valid_sentence_rate,
        "avg_score": avg_score,
        "avg_quality": avg_quality,
        "helped": helped,
        "current_streak": current_streak,
        "best_streak": best_streak,
        "active_days": len(activity_days),
        "by_type": by_type,
        "by_direction": by_direction,
        "by_validator": by_validator,
        "validator_counts": validator_counts,
        "level_dist": level_dist,
        "new_pending": new_pending,
        "vencidas_total": vencidas_total,
        "backlog": backlog,
        "practiced_today": practiced_today,
        "skyline": skyline,
        "weeks": weeks,
        "evolution": evolution,
        "rate": rate,
        "rate_avg": rate_avg,
        "hardest": hardest,
        "easiest": easiest,
        "generated": now.strftime("%Y-%m-%d %H:%M UTC"),
    }


def _clean_ax(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_facecolor("white")


def _chart_accuracy(data):
    fig, ax = plt.subplots(figsize=(9, 3.8))
    groups = [
        ([("quiz", data["by_type"].get("quiz", 0)), ("match", data["by_type"].get("match", 0))], "Tipo de sesion"),
        ([("es_to_en", data["by_direction"].get("es_to_en", 0)), ("en_to_es", data["by_direction"].get("en_to_es", 0))], "Direccion"),
        ([("gemini", data["by_validator"].get("gemini", 0)), ("spacy", data["by_validator"].get("spacy", 0))], "Validador"),
    ]
    colors = ["#1d4ed8", "#f59e0b"]
    positions = [0, 3, 6]
    for g, (pairs, label) in enumerate(groups):
        for j, (name, val) in enumerate(pairs):
            ax.bar(positions[g] + j * 0.8, val, width=0.7, color=colors[j])
            ax.text(positions[g] + j * 0.8, val + 2, f"{val}%", ha="center", fontsize=8)
    ax.set_xticks([p + 0.4 for p in positions], groups[0] and [l for _, l in groups] or [])
    ax.set_ylim(0, 100)
    ax.set_ylabel("Precision (%)")
    ax.set_title("Precision por tipo, direccion y validador")
    ax.legend(
        handles=[plt.Rectangle((0, 0), 1, 1, color=c) for c in colors],
        labels=["quiz / es_to_en / gemini", "match / en_to_es / spaCy"],
        ncol=2, loc="lower right", fontsize=8,
    )
    _clean_ax(ax)
    fig.tight_layout()
    return fig


def _chart_evolution(evolution):
    fig, ax = plt.subplots(figsize=(9, 3.6))
    for stype, color, marker in (("quiz", "#1d4ed8", "o"), ("match", "#30a14e", "s")):
        series = evolution[stype]
        values = [None if d["accuracy"] is None else d["accuracy"] for d in series]
        ax.plot(range(len(values)), values, marker=marker, ms=3, linewidth=1.5, color=color, label=stype)
    ax.set_ylim(0, 105)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_xticks(range(0, 30, 5))
    ax.set_xticklabels([evolution["quiz"][i]["label"][5:] for i in range(0, 30, 5)], fontsize=8)
    ax.set_ylabel("Precision (%)")
    ax.set_title("Evolucion de precision (30 dias)")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(axis="y", alpha=0.3)
    _clean_ax(ax)
    fig.tight_layout()
    return fig


def _chart_heatmap(weeks):
    grid = np.array([[d["count"] for d in week] for week in weeks]).T
    vmax = max(grid.max(), 1)
    fig, ax = plt.subplots(figsize=(9, 2.7))
    im = ax.imshow(grid, aspect="auto", cmap="Greens", vmin=0, vmax=vmax)
    ax.set_yticks(range(7), ["L", "M", "X", "J", "V", "S", "D"], fontsize=9)
    ax.set_xticks(range(0, 16, 2))
    ax.set_xticklabels([weeks[i][0]["iso"][5:] for i in range(0, 16, 2)], fontsize=8)
    fig.colorbar(im, ax=ax, shrink=0.8, label="Practicas")
    ax.set_title("Calendario de actividad (16 semanas)")
    fig.tight_layout()
    return fig


def _chart_levels(level_dist):
    names = [d["name"] for d in level_dist]
    counts = [d["count"] for d in level_dist]
    fig, ax = plt.subplots(figsize=(5.4, 3.2))
    bars = ax.barh(names, counts, color=_LEVEL_COLORS)
    for b, c in zip(bars, counts):
        ax.text(b.get_width() + 0.1, b.get_y() + b.get_height() / 2, str(c), va="center", fontsize=9)
    ax.set_xlabel("Palabras")
    ax.set_title("Distribucion por nivel SM-2")
    ax.margins(y=0.15)
    _clean_ax(ax)
    fig.tight_layout()
    return fig


def _chart_skyline(skyline):
    labels = [d["label"][5:] for d in skyline]
    counts = [d["count"] for d in skyline]
    fig, ax = plt.subplots(figsize=(7, 3))
    ax.fill_between(range(len(counts)), counts, step="mid", alpha=0.25, color="#dc2626")
    ax.plot(range(len(counts)), counts, color="#b91c1c", linewidth=1.6)
    ax.set_xticks(range(0, 14, 2))
    ax.set_xticklabels([labels[i] for i in range(0, 14, 2)], fontsize=8)
    ax.set_ylabel("Repasos")
    ax.set_title("Carga de repaso programada (14 dias)")
    ax.grid(axis="y", alpha=0.3)
    _clean_ax(ax)
    fig.tight_layout()
    return fig


def render_charts(data):
    """Devuelve lista de (titulo, figura matplotlib)."""
    return [
        ("Precision por dimension", _chart_accuracy(data)),
        ("Evolucion de precision", _chart_evolution(data["evolution"])),
        ("Calendario de actividad", _chart_heatmap(data["weeks"])),
        ("Distribucion por nivel", _chart_levels(data["level_dist"])),
        ("Carga de repaso programada", _chart_skyline(data["skyline"])),
    ]


def _render_summary_fig(data):
    fig = plt.figure(figsize=(8.27, 11.69))
    fig.patch.set_facecolor("white")
    fig.text(0.5, 0.93, "Informe de progreso - VocabApp", ha="center", fontsize=18, weight="bold")
    fig.text(0.5, 0.895, f"Generado {data['generated']} (UTC)", ha="center", fontsize=10, color="#374151")

    lines = [
        ("Palabras totales", data["n_words"]),
        ("Palabras practicadas", data["n_practiced"]),
        ("Precision general", f"{data['all_time_accuracy']}%"),
        ("Sesiones registradas", data["n_sessions"]),
        ("Precision quiz", f"{data['quiz_accuracy']}%"),
        ("Oraciones validas (quiz)", f"{data['valid_sentence_rate']}%"),
        ("Puntaje promedio", data["avg_score"]),
        ("Practicas con ayuda", data["helped"]),
        ("Racha actual", data["current_streak"]),
        ("Mejor racha", data["best_streak"]),
        ("Repaso pendiente (cola)", data["backlog"]),
        ("Practicadas hoy", data["practiced_today"]),
    ]
    y = 0.82
    for label, value in lines:
        fig.text(0.12, y, label, fontsize=11)
        fig.text(0.88, y, str(value), ha="right", fontsize=11, weight="bold")
        y -= 0.042
    return fig


def _render_tables_fig(data):
    fig, axs = plt.subplots(1, 2, figsize=(8.27, 6), gridspec_kw={"left": 0.04, "right": 0.98, "top": 0.92, "bottom": 0.06})
    headers = ["Palabra", "Precision", "Fallos", "Veces"]
    hardest_rows = [
        [w["english"], f"{w['accuracy']}%", w["failures"], w["times_practiced"]]
        for w in data["hardest"]
    ]
    easiest_rows = [
        [w["english"], f"{w['accuracy']}%", w["failures"], w["times_practiced"]]
        for w in data["easiest"]
    ]
    for ax, title, rows in (
        (axs[0], "Mas dificiles (mas fallos)", hardest_rows),
        (axs[1], "Mejor dominadas", easiest_rows),
    ):
        ax.axis("off")
        ax.set_title(title, fontsize=12, weight="bold")
        table_rows = rows if rows else [["-", "-", "-", "-"]]
        table = ax.table(cellText=table_rows, colLabels=headers, loc="upper center", cellLoc="left")
        table.auto_set_font_size(False)
        table.set_fontsize(8.5)
        table.scale(1, 1.4)
    return fig


def build_report_outputs(data):
    """Renderiza graficos a PNG (para la web) y un PDF multipagina. Lee solo de la BD."""
    charts = render_charts(data)
    pngs = []
    pdf_buf = io.BytesIO()
    with PdfPages(pdf_buf) as pdf:
        pdf.savefig(_render_summary_fig(data))
        plt.close("all")
        for title, fig in charts:
            png_buf = io.BytesIO()
            fig.savefig(png_buf, format="png", dpi=110, bbox_inches="tight")
            pngs.append((title, base64.b64encode(png_buf.getvalue()).decode()))
            pdf.savefig(fig)
            plt.close(fig)
        pdf.savefig(_render_tables_fig(data))
        plt.close("all")
    return pngs, pdf_buf.getvalue()