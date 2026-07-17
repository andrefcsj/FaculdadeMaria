"""Configuração carregada automaticamente pelo Gunicorn no Render."""

worker_class = "gthread"
workers = 1
threads = 8
timeout = 45
graceful_timeout = 15
keepalive = 5
