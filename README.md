# FaculdadeMaria / Cortex Invest PRO v1.8

Versão de teste com velocímetro premium no estilo dashboard escuro, mantendo a base funcional da v1.7.

## Deploy no Render

Build Command:
```bash
pip install -r requirements.txt
```

Start Command:
```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

## Alterações v1.8
- Novo velocímetro ROI com arco segmentado em degradê vermelho → amarelo → verde.
- Ponteiro metálico.
- Valor do ROI abaixo do ponteiro.
- Badge BOM/BAIXO/EXCELENTE sem frase “sobre capital comprometido”.
- Identificação visual atualizada para v1.8.
