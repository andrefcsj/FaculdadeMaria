# FaculdadeMaria / Cortex Invest PRO

Sistema web do Dashboard Wheel, feito para rodar no Render.

## Render

Build Command:
```bash
pip install -r requirements.txt
```

Start Command:
```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

## Arquivos principais

- `app.py`: sistema web completo.
- `data/operacoes.csv`: operações abertas.
- `data/fechadas.csv`: histórico de operações fechadas.
- `data/config.csv`: capital inicial, alíquota e parâmetros.

Sem login: ao abrir o link, entra direto no dashboard.
