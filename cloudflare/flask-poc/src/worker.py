from flask import Flask, request
from pyodide.ffi import run_sync
from workers import wsgi


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


Default = wsgi.entrypoint(app)
