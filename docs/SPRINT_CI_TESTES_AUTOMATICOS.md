# Sprint — CI e Testes Automáticos

**Status:** Concluída  
**Data:** 12/07/2026

## Entregas

- workflow GitHub Actions em Pull Requests para `main`;
- execução após pushes na `main`;
- disparo manual disponível;
- Python 3.12 padronizado;
- instalação reproduzível de dependências;
- cache de pacotes Python;
- validação de sintaxe de aplicação, motor, serviços e testes;
- execução integral do pytest;
- cancelamento de execução antiga quando uma nova versão da mesma branch é enviada;
- limite de quinze minutos para impedir jobs presos.

## Correção preventiva

`pypdf` foi adicionado às dependências de produção. A importação de notas de corretagem depende dessa biblioteca e poderia falhar em um deploy limpo sem essa declaração.

## Próxima funcionalidade registrada

`FM-TAX-010 — Histórico de DARFs pagos`, incluindo upload de PDFs, consulta mensal/anual e gráfico de evolução.

## Validação

- suíte completa executada localmente;
- YAML validado;
- workflow será confirmado pela própria execução do GitHub após publicação.
