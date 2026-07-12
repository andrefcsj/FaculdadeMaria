# Sprint — Navegação Premium, Scanner e Alertas Operacionais

**Projeto:** FaculdadeMaria  
**Status:** Concluída — aguardando aprovação para merge  
**Data:** 12/07/2026  
**Branch:** `agent/navegacao-premium-scanner-alertas`

## Objetivo

Elevar a experiência de navegação, separar funcionalmente Scanner e Radar, restaurar gráficos decorativos nos cards e tornar o painel de atenção operacionalmente útil.

## Entregas

- menu lateral Premium com fonte regular ampliada;
- ícones vetoriais monocromáticos;
- estado ativo verde;
- logotipo FaculdadeMaria com assinatura Opções Inteligentes;
- barra superior global com título, data, alertas e atualização;
- menu recolhível;
- Scanner Inteligente em rota própria;
- filtros por ativo, status, ROI e vencimento;
- visão completa de elegíveis, observações e descartes;
- Radar preservado como seleção priorizada;
- gráficos decorativos SVG nos seis cards coloridos;
- fontes ampliadas no Dashboard;
- alertas por proximidade do strike, vencimento e ausência de cotação;
- gravidade Crítico, Ação, Observar e Informação;
- sugestão de avaliação de rolagem quando tecnicamente aplicável.

## Distinção funcional

- **Radar de Oportunidades:** ranking curado do Decision Engine.
- **Scanner Inteligente:** exploração e filtragem do universo completo carregado.

## Segurança

- nenhum preço ou série é inventado;
- Scanner usa apenas CSV importado ou B3 COTAHIST disponível;
- alertas são determinísticos e não executam ordens;
- maior prêmio não recebe prioridade automática;
- Radar e Decision Engine permanecem preservados.

## Validação

- suíte automatizada completa;
- testes das rotas distintas;
- testes dos filtros e marcadores visuais;
- testes de alertas por gravidade;
- sintaxe e renderização Flask;
- regressão das funcionalidades existentes.

## Deploy

O Product Owner solicitou deploy manual. Nenhum deploy será iniciado automaticamente nesta Sprint.
