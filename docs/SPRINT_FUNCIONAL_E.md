# Relatório Técnico — Sprint Funcional E

## Status

- Sprint: `Funcional E — Ranking e Explicação resumida`.
- Issue: `#25`.
- Product Owner: Andre.
- Branch: `sprint-funcional-e-ranking-explanation`.
- Base oficial: `main` no commit `6652c3fef6d214f2975440fa3b92149f380a4204`.
- Tela visual: não implementada nesta Sprint.

---

## Objetivo

Adicionar duas capacidades ao Decision Engine:

1. ranking inicial de oportunidades já avaliadas;
2. resumo curto do motivo da operação para futura tela do Radar.

Pedido do Product Owner:

```text
Pode fazer um resumo da explicação do motivo da operação.
```

---

## Implementado

### Explicação resumida

Criados:

```text
engine/explain/__init__.py
engine/explain/summary.py
```

API:

```text
OperationSummary
summarize_put_operation
```

A explicação gera:

- status curto;
- título/headline;
- motivo principal;
- principal ponto positivo;
- principal ponto de atenção;
- principal bloqueio quando descartada;
- score quando aplicável.

Exemplos de saída esperada:

```text
Operação elegível — Score 88/100. ROI 5,00%, desconto 8,00%. Ativo adequado para exercício.
```

```text
Operação descartada — Ativo não aceito para exercício.
```

### Ranking inicial

Criados:

```text
engine/ranking/__init__.py
engine/ranking/opportunities.py
```

API:

```text
RankingConfig
RankedOpportunity
rank_put_opportunities
```

Critérios de ordenação:

1. status da estratégia/score;
2. Score IA;
3. desconto/preço líquido;
4. ROI bruto;
5. eficiência do capital;
6. confiança dos dados.

Operações bloqueadas permanecem explicáveis por padrão, mas podem ser ocultadas via configuração.

---

## Segurança

Preservado:

- sem provider real;
- sem rede;
- sem Flask;
- sem banco;
- sem CSV;
- sem templates;
- sem CSS/JS;
- sem Radar visual;
- sem rolagem;
- sem Machine Learning;
- `motor_ia/` intocado.

---

## Testes

Criado:

```text
tests/test_engine_ranking_explanation.py
```

Cobertura:

- resumo de operação elegível;
- resumo de operação descartada;
- resumo de operação em observação;
- ranking por score;
- manutenção de descartadas com motivo;
- ocultação opcional de descartadas;
- validação de tamanho mínimo do resumo.

---

## Resultado

A Sprint E deixa o motor mais próximo do Radar Premium, porque agora ele não apenas calcula nota, mas também:

- organiza oportunidades;
- preserva descartes com motivo;
- gera texto curto para o usuário entender rapidamente o porquê da operação.

O próximo passo natural é a Sprint Funcional F — Serviço de Radar e primeira tela visual.
