# FaculdadeMaria / Cortex Invest PRO v1.6

Alterações desta versão:

- Adicionado card de **Caixa Livre**.
- Explicação visual de KPI: indicadores principais do topo do dashboard.
- Escala do velocímetro ajustada: os textos **1,5%** e **3%** foram elevados.
- Valor grande do ROI voltou para a posição anterior.
- Quadro **Top 5 Operações (Prêmio Ativo)** renomeado para **Top 5 Operações Abertas**.
- Evolução do Patrimônio passa a considerar **capital investido + prêmios recebidos**.
- Evolução do Lucro passa a considerar prêmios de operações **abertas e fechadas**.

Deploy Render:

Build Command:

```bash
pip install -r requirements.txt
```

Start Command:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```
