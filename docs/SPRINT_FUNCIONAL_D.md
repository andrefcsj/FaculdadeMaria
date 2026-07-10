# Relatório Técnico — Sprint Funcional D

## Status

- Sprint: `Funcional D — Score IA explicável`.
- Issue: `#23`.
- Product Owner: Andre.
- Branch: `sprint-funcional-d-explainable-score`.
- Base oficial: `main` no commit `8b8010bae341f33c45910c6eb204649b00d1c82d`.
- ROI alvo padrão definido pelo Product Owner: `4% = 0.04`.
- Ranking: não implementado.
- Radar/UI: não implementado.

---

## Objetivo

Implementar o Score IA inicial explicável, usando a base das Sprints A, B e C:

- métricas de PUT;
- filtros de segurança;
- qualidade do ativo;
- avaliador inicial da estratégia PUT.

A regra central permanece:

```text
Score IA não resgata operação inelegível.
```

---

## Implementado

### `engine/score/explainable.py`

Inclui:

- `DEFAULT_TARGET_GROSS_ROI = Decimal("0.04")`;
- `ExplainableScoreConfig`;
- `ScoreComponent`;
- `ScoreEvaluation`;
- `calculate_put_score`.

### Componentes do Score

O Score inicial considera:

- qualidade do ativo;
- segurança;
- ROI bruto vs alvo de 4%;
- preço líquido/desconto;
- eficiência do capital.

### Pesos padrão

```text
qualidade do ativo: 30%
segurança: 25%
ROI vs alvo: 20%
preço líquido/desconto: 15%
eficiência do capital: 10%
```

Os pesos são explícitos e normalizados.

---

## Regra do ROI alvo

O alvo padrão do sistema ficou definido como:

```text
0.04 = 4%
```

Esse valor é usado pelo componente:

```text
gross_roi_vs_target
```

Se o ROI bruto for 2%, o fator do componente é aproximadamente metade do alvo.

Se o ROI bruto atingir ou superar 4%, o componente atinge 100% do seu peso.

---

## Regras de bloqueio

Quando a estratégia estiver:

```text
ineligible
```

O Score final é:

```text
0
```

com status:

```text
score_blocked
```

Motivo:

```text
Strategy gates failed: score cannot rescue an ineligible PUT
```

Quando a estratégia estiver com dados insuficientes:

```text
score_insufficient_data
```

---

## Confiança separada do Score

A confiança dos dados permanece separada:

```text
data_confidence
```

Ela não é misturada automaticamente à nota.

---

## Testes

Criado:

```text
tests/test_engine_explainable_score.py
```

Cobertura:

- ROI alvo padrão é 4%;
- Score pronto para PUT elegível;
- componente de ROI usa meta de 4%;
- PUT inelegível bloqueia Score mesmo com ROI alto;
- watchlist mantém Score calculado com atenção;
- configuração inválida rejeita alvo zero.

---

## Escopo preservado

Não foi alterado:

- Flask;
- `app.py`;
- rotas;
- templates;
- CSS;
- JavaScript;
- banco;
- CSV;
- providers reais;
- `motor_ia/`;
- ranking;
- Radar visual;
- rolagem;
- Machine Learning.

---

## Comparação com `main`

Antes deste relatório:

- branch à frente de `main`;
- `ahead_by: 4`;
- `behind_by: 0`;
- alterações restritas a `engine/` e `tests/`.

Após este relatório, o diff inclui também:

```text
docs/SPRINT_FUNCIONAL_D.md
```

---

## Resultado

A Sprint D adiciona uma nota inicial, auditável e explicável, sem caixa-preta.

O sistema agora pode calcular Score IA com base em:

- qualidade;
- segurança;
- ROI alvo de 4%;
- desconto/preço líquido;
- eficiência do capital.

O próximo passo natural após esta Sprint é a Sprint Funcional E — Ranking e Explicação técnica inicial.
