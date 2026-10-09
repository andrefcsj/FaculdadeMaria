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

## Sprint — Valor efetivo no exercício (08/10/2026)

- Calculadora rápida exibe custo efetivo por ação na venda de PUT (strike menos prêmio) e valor efetivo de venda na CALL (strike mais prêmio).
- Cálculo automático apenas com strike e prêmio, sem cotação ou vencimento obrigatório; mantém ROI e distância existentes.
- Valores gerenciais sem custos ou impostos, separados do preço contratual de exercício (strike).
- Validação: sintaxe JavaScript, diff e execução da calculadora com valores da imagem, cotação ausente, prêmio zero, formatos numéricos, limpeza e entradas inválidas.

## Sprint CF-02 — Conclusão funcional da migração (08/10/2026)

- Piloto atualizado com Radar de novas oportunidades, scanner de CALL, Jade, rolagem e integrações reais SLDX/B3/CVM/CSV.
- Cálculos e memória gerencial fiscal revisados; notas e operações atômicas; backup/restauração e reaberturas protegidas contra falhas parciais.
- Reconciliação PostgreSQL/D1 concluída, preservando os lançamentos posteriores do Cloudflare. Nenhuma operação ou nota de teste inserida na base real.
- Validação: 164 testes Python, 24 testes JavaScript, 28 casos de paridade e navegador desktop/mobile aprovados.
- Publicado e validado em www.radarpulse.com.br/faculdademaria/ após aprovação de Andre. Login desktop/mobile, dados financeiros e preservação da rota de contabilidade confirmados. Apenas o desligamento do Render/Neon permanece pendente. Ver `docs/SPRINT_CLOUDFLARE_CONCLUSAO.md` e `docs/CLOUDFLARE_CORTE_E_REVERSAO.md`.

## Sprint CF-03 — Popups e acesso (09/10/2026)

- Última negociação da nota fecha e limpa o popup automaticamente e mostra Operações Abertas; negociações pendentes e erros mantêm a janela.
- Dez tipos de popup móveis pelo cabeçalho, incluindo confirmações e edição de valores; suporte a toque e duplo clique para centralizar, com fundo legível.
- PIN atualizado no secret do Worker, sem gravação no código.
- Publicado no www e no piloto; fluxo PDF real sintético em base isolada, arraste desktop/mobile, nova tentativa após falha e acesso com o novo PIN validados. Dados financeiros reais preservados.
