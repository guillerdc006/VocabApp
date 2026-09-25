from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
import io
from openpyxl import Workbook
from ..models import Word, WordStats
from ..extensions import db
from ..services.excel_import import import_file

vocab_bp = Blueprint("vocabulary", __name__)


@vocab_bp.route("/")
def word_list():
    search = request.args.get("search", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 20

    query = Word.query.join(WordStats, isouter=True)

    if search:
        query = query.filter(
            db.or_(
                Word.english.ilike(f"%{search}%"),
                Word.spanish.ilike(f"%{search}%"),
            )
        )

    query = query.order_by(Word.english)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "vocabulary/list.html",
        words=pagination.items,
        pagination=pagination,
        search=search,
    )


@vocab_bp.route("/add", methods=["GET", "POST"])
def add_word():
    if request.method == "POST":
        english = request.form.get("english", "").strip()
        spanish = request.form.get("spanish", "").strip()
        notes = request.form.get("notes", "").strip() or None

        if not english or not spanish:
            flash("Ambos campos son obligatorios.", "danger")
            return redirect(url_for("vocabulary.add_word"))

        exists = Word.query.filter_by(english=english).first()
        if exists:
            flash(f'La palabra "{english}" ya existe.', "warning")
            return redirect(url_for("vocabulary.add_word"))

        word = Word(english=english, spanish=spanish, notes=notes)
        db.session.add(word)
        db.session.flush()

        stats = WordStats(word_id=word.id)
        db.session.add(stats)
        db.session.commit()

        flash(f'Palabra "{english}" agregada correctamente.', "success")
        return redirect(url_for("vocabulary.word_list"))

    return render_template("vocabulary/add.html")


@vocab_bp.route("/edit/<int:word_id>", methods=["GET", "POST"])
def edit_word(word_id):
    word = Word.query.get_or_404(word_id)

    if request.method == "POST":
        english = request.form.get("english", "").strip()
        spanish = request.form.get("spanish", "").strip()
        notes = request.form.get("notes", "").strip() or None

        if not english or not spanish:
            flash("Ambos campos son obligatorios.", "danger")
            return render_template(
                "vocabulary/edit.html",
                word=word,
                form_values={"english": english, "spanish": spanish, "notes": notes or ""},
            )

        exists = Word.query.filter(
            Word.english == english, Word.id != word_id
        ).first()
        if exists:
            flash(f'La palabra "{english}" ya existe.', "warning")
            return render_template(
                "vocabulary/edit.html",
                word=word,
                form_values={"english": english, "spanish": spanish, "notes": notes or ""},
            )

        word.english = english
        word.spanish = spanish
        word.notes = notes
        db.session.commit()

        flash(f'Palabra "{english}" actualizada correctamente.', "success")
        return redirect(url_for("vocabulary.word_list"))

    return render_template("vocabulary/edit.html", word=word, form_values=None)


@vocab_bp.route("/delete/<int:word_id>", methods=["POST"])
def delete_word(word_id):
    word = Word.query.get_or_404(word_id)
    db.session.delete(word)
    db.session.commit()
    flash(f'Palabra "{word.english}" eliminada.', "success")
    return redirect(url_for("vocabulary.word_list"))


@vocab_bp.route("/export")
def export_excel():
    wb = Workbook()
    ws = wb.active
    ws.title = "vocabulary"
    ws.append(
        [
            "english",
            "spanish",
            "notes",
            "level",
            "level_name",
            "times_practiced",
            "times_correct",
            "accuracy_percent",
            "next_review",
            "last_practiced",
        ]
    )

    words = Word.query.order_by(Word.english).all()
    for word in words:
        stats = word.stats
        ws.append(
            [
                word.english,
                word.spanish,
                word.notes or "",
                stats.level if stats else "",
                stats.level_name if stats else "",
                stats.times_practiced if stats else 0,
                stats.times_correct if stats else 0,
                stats.accuracy if stats else 0,
                stats.next_review.strftime("%Y-%m-%d %H:%M")
                if stats and stats.next_review
                else "",
                stats.last_practiced.strftime("%Y-%m-%d %H:%M")
                if stats and stats.last_practiced
                else "",
            ]
        )

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    return send_file(
        buf,
        as_attachment=True,
        download_name="vocabulario_export.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@vocab_bp.route("/import", methods=["GET", "POST"])
def import_excel():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename.endswith((".xlsx", ".xls")):
            flash("Por favor sube un archivo Excel (.xlsx).", "danger")
            return redirect(url_for("vocabulary.import_excel"))

        import os
        upload_dir = os.path.join(os.path.dirname(__file__), "..", "..", "instance")
        os.makedirs(upload_dir, exist_ok=True)
        filepath = os.path.join(upload_dir, "upload_temp.xlsx")
        file.save(filepath)

        try:
            added, skipped = import_file(filepath)
            flash(
                f"Importacion completa: {added} agregadas, {skipped} duplicadas omitidas.",
                "success",
            )
        except Exception as e:
            flash(f"Error al importar: {str(e)}", "danger")
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

        return redirect(url_for("vocabulary.word_list"))

    return render_template("vocabulary/import.html")
