from datetime import datetime, timezone
from io import BytesIO

from flask import Blueprint, render_template, send_file

from ..services.reporting import build_report_data, build_report_outputs

report_bp = Blueprint("report", __name__, url_prefix="/report")


@report_bp.route("")
def report():
    data = build_report_data()
    charts, _ = build_report_outputs(data)
    return render_template("report/report.html", data=data, charts=charts)


@report_bp.route("/pdf")
def report_pdf():
    data = build_report_data()
    _, pdf_bytes = build_report_outputs(data)
    name = f"informe-progreso-{datetime.now(timezone.utc):%Y%m%d}.pdf"
    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=name,
    )