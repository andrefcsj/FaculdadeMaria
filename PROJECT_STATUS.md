# PROJECT_STATUS.md

**Projeto:** FaculdadeMaria\
**Versão:** 1.0\
**Status:** Em desenvolvimento ativo

------------------------------------------------------------------------

# Status Geral

  Módulo                      Status     Progresso
  ------------------------ ------------ -----------
  Decision Engine               ✅         100%
  Cálculos de PUT               ✅         100%
  Indicadores Técnicos          ✅         100%
  Filtros de Segurança          ✅         100%
  Qualidade do Ativo            ✅         100%
  Score IA                      ✅         100%
  Ranking                       ✅         100%
  Radar Premium (visual)        ✅         100%
  Operações Abertas             ✅         100%
  Scanner de Mercado EOD        🚧          70%
  Provider B3/CVM               ✅         100%
  Importador PDF            📝 Backlog      0%

------------------------------------------------------------------------

# Sprints Concluídas

-   ✅ Sprint 1.1-R
-   ✅ Sprint Funcional A
-   ✅ Sprint Funcional B
-   ✅ Sprint Funcional C
-   ✅ Sprint Funcional D
-   ✅ Sprint Funcional E
-   ✅ Sprint Funcional F
-   ✅ Sprint Funcional G
-   ✅ Sprint Alinhamento ROI 4% e Documentação
-   ✅ Sprint Provider B3 EOD + Atualização Manual Intraday
-   ✅ Sprint Provider CVM + Score Automático de Qualidade

------------------------------------------------------------------------

# Próximas Prioridades

1.  Comparador visual de oportunidades
2.  Homologação contínua do Radar com dados reais EOD
3.  Integração intraday oficial quando disponível

------------------------------------------------------------------------

# Meta Atual

Homologar o Radar Premium com dados reais EOD da B3, qualidade automática
da CVM e confirmação manual de preços intraday.

------------------------------------------------------------------------

# Observações

-   ROI alvo oficial: **4%**
-   O Radar deve buscar oportunidades novas, nunca listar operações
    abertas.
-   O Decision Engine permanece como núcleo do sistema.

## Sprint — Filtros de prêmios recebidos (17/09/2026)

- Consulta por ação combinada com mês, ano ou intervalo de datas inclusivo.
- Intervalos aceitam somente início ou somente fim; usam a data de abertura da venda.
- Resumo de valores bruto/líquido e quantidade acompanha os resultados filtrados.
- Validação de datas e estado vazio sem retorno indevido ao histórico completo.
- Links existentes com `month` e `year` continuam compatíveis.
- Validação: 14 testes e 14 subcasos aprovados; fluxo conferido no Chromium com PETR4, intervalo inclusivo, mês vazio e limpeza dos filtros.
