from flask import Flask
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


Default = wsgi.entrypoint(app)
