# FaculdadeMaria / Cortex Invest PRO - v1.9

Atualização incremental com ajustes solicitados:

- velocímetros de ROI menores e menos deformados;
- numeração do velocímetro corrigida e posicionada acima das barras coloridas;
- ROI centralizado no velocímetro;
- removida a linha de meta abaixo do velocímetro;
- removido o quadro Resumo Geral;
- título de Operações Abertas agora mostra a quantidade de operações abertas;
- campo Strike movido para logo após Código da Opção no cadastro.

## Render
Build Command:
```bash
pip install -r requirements.txt
```

Start Command:
```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```
