# FaculdadeMaria / Cortex Invest PRO — v1.7 Noite

Versão incremental para testes durante o plantão.

## Entrou nesta versão

- Topo reorganizado em formato de KPIs.
- Novo card: Prêmios Acumulados.
- Novo card: Caixa Disponível.
- Novo card: Próximo Vencimento.
- Novo card: Nota Cortex inicial.
- Mantidos os ajustes anteriores: ROI abertas, velocímetros, Top 5 Operações Abertas, patrimônio e lucro.
- Melhor responsividade dos KPIs no celular.

## Render

Build Command:
`pip install -r requirements.txt`

Start Command:
`gunicorn app:app --bind 0.0.0.0:$PORT`
