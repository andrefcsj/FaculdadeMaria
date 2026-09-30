from flask import Flask, request, url_for
from functools import wraps
from hmac import compare_digest
from io import BytesIO
from pyodide.ffi import run_sync
from pypdf import PdfReader
from reportlab.pdfgen import canvas
from workers import wsgi

from d1_repository import list_closed_operations, list_config, list_operations
from cloudflare_http import get_status


app = Flask(__name__)


class PrefixMiddleware:
    """Monta o Flask em um subcaminho sem duplicar todas as rotas."""

    def __init__(self, application, prefix: str):
        self.application = application
        self.prefix = prefix.rstrip("/")

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        if path == self.prefix or path.startswith(self.prefix + "/"):
            environ["SCRIPT_NAME"] = environ.get("SCRIPT_NAME", "") + self.prefix
            environ["PATH_INFO"] = path[len(self.prefix):] or "/"
            return self.application(environ, start_response)
        start_response("404 Not Found", [("Content-Type", "application/json")])
        return [b'{"error":"use /faculdademaria/"}']


def pilot_access_required(view):
    """Evita que dados de homologação sejam expostos no Worker público."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        supplied = request.headers.get("Authorization", "").removeprefix("Bearer ")
        expected = str(request.environ["workers.env"].PILOT_ACCESS_TOKEN)
        if not expected or not compare_digest(supplied, expected):
            return {"error": "unauthorized"}, 401
        return view(*args, **kwargs)

    return wrapped


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
@pilot_access_required
def operations():
    return {"operations": list_operations()}


@app.get("/api/config")
@pilot_access_required
def config():
    return {"config": list_config()}


@app.get("/api/closed-operations")
@pilot_access_required
def closed_operations():
    return {"closed_operations": list_closed_operations()}


@app.get("/api/routing-check")
@pilot_access_required
def routing_check():
    return {"health_url": url_for("health")}


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


@app.get("/api/outbound-probe")
def outbound_probe():
    """Valida o adaptador fetch para as integrações de mercado."""
    try:
        status = get_status(
            "https://www.cloudflare.com/cdn-cgi/trace",
            {"User-Agent": "FaculdadeMaria-Cloudflare-Pilot/1.0"},
        )
        return {"http_status": status, "status": "ok"}
    except Exception:
        return {
            "status": "outbound-probe-failed",
            "message": "O adaptador fetch não concluiu a chamada externa.",
        }, 501


Default = wsgi.entrypoint(PrefixMiddleware(app, "/faculdademaria"))
