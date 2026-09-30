from flask import Flask, request
from io import BytesIO
from pyodide.ffi import run_sync
from pypdf import PdfReader
from reportlab.pdfgen import canvas
from workers import wsgi

from d1_repository import list_config, list_operations


app = Flask(__name__)


@app.get("/")
@app.get("/health")
def health():
    return {
        "service": "faculdademaria-flask-pilot",
        "runtime": "cloudflare-python-workers",
        "framework": "flask",
        "status": "ok",
    }


@app.get("/api/d1-health")
def d1_health():
    """Confirma o acesso síncrono do Flask (WSGI) ao binding D1 assíncrono."""
    database = request.environ["workers.env"].DB
    result = run_sync(database.prepare("SELECT 1 AS ok").run())
    return {
        "database": "d1",
        "status": "ok" if result.success else "degraded",
    }


@app.get("/api/operations")
def operations():
    return {"operations": list_operations()}


@app.get("/api/config")
def config():
    return {"config": list_config()}


@app.get("/api/pdf-compatibility")
def pdf_compatibility():
    output = BytesIO()
    pdf = canvas.Canvas(output)
    pdf.drawString(72, 720, "FaculdadeMaria - piloto Cloudflare")
    pdf.save()
    document = output.getvalue()
    pages = len(PdfReader(BytesIO(document)).pages)
    return {
        "bytes": len(document),
        "pages": pages,
        "pypdf": PdfReader.__module__,
        "reportlab": canvas.Canvas.__module__,
        "status": "generated-and-read",
    }


Default = wsgi.entrypoint(app)
