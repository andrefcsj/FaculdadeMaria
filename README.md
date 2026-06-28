# FaculdadeMaria / Cortex Invest PRO v1.4

Versão com ajustes de dashboard, velocímetros e operações abertas.

## Render

Build Command:
```bash
pip install -r requirements.txt
```

Start Command:
```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

## Alterações v1.4
- ROI Abertas no card superior igual ao velocímetro.
- Ponteiros amarelos e escala 0% a 5% corrigida.
- Legenda dos velocímetros centralizada.
- DARF calculada pelas operações fechadas.
- Coluna Ação antes de Opção.
- Coluna Ativo renomeada para Opção.
- Contratos exibidos como quantidade de ações (contratos x 100).
