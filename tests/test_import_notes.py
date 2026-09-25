import io

from openpyxl import Workbook

from app.models import Word


def _make_xlsx(rows, headers):
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


class TestImportConNotas:
    def test_importa_observacion(self, client):
        buf = _make_xlsx(
            [("abroad", "en el extranjero", "se usa con to go"), ("apple", "manzana", "fruta")],
            ["Inglés", "Español", "Observación"],
        )
        resp = client.post(
            "/vocabulary/import",
            data={"file": (buf, "words.xlsx")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 302

        with client.application.app_context():
            assert Word.query.filter_by(english="abroad").first().notes == "se usa con to go"
            assert Word.query.filter_by(english="apple").first().notes == "fruta"

    def test_importa_observacion_ingles(self, client):
        buf = _make_xlsx(
            [("dog", "perro", "animal")],
            ["english", "spanish", "notes"],
        )
        client.post(
            "/vocabulary/import",
            data={"file": (buf, "words.xlsx")},
            content_type="multipart/form-data",
        )
        with client.application.app_context():
            assert Word.query.filter_by(english="dog").first().notes == "animal"

    def test_importa_sin_columna_observacion(self, client):
        buf = _make_xlsx([("dog", "perro")], ["Inglés", "Español"])
        client.post(
            "/vocabulary/import",
            data={"file": (buf, "words.xlsx")},
            content_type="multipart/form-data",
        )
        with client.application.app_context():
            word = Word.query.filter_by(english="dog").first()
            assert word.notes is None

    def test_observacion_vacia_queda_none(self, client):
        buf = _make_xlsx(
            [("dog", "perro", "")],
            ["english", "spanish", "notes"],
        )
        client.post(
            "/vocabulary/import",
            data={"file": (buf, "words.xlsx")},
            content_type="multipart/form-data",
        )
        with client.application.app_context():
            assert Word.query.filter_by(english="dog").first().notes is None