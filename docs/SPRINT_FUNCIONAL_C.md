# Relatório Técnico — Sprint Funcional C

## Status

- Sprint: `Funcional C — Qualidade do Ativo e Estratégia PUT`.
- Issue: `#21`.
- Product Owner: Andre.
- Branch: `sprint-funcional-c-asset-put-strategy`.
- Base oficial: `main` no commit `67c305c01691973cbf207e1c855d7f515fc57ad9`.
- Natureza: terceira evolução funcional do novo Decision Engine.
- Score IA: não implementado.
- Ranking: não implementado.
- Radar/UI: não implementado.

---

## Objetivo

Implementar a camada que impede o motor de aceitar uma PUT apenas porque o prêmio ou ROI é alto.

A Sprint C adiciona:

- qualidade explícita do ativo;
- elegibilidade para exercício;
- adequação ao longo prazo;
- concentração quando fornecida;
- avaliador inicial da estratégia de venda de PUT;
- combinação de segurança, métricas e qualidade do ativo.

---

## Implementado

### `engine/asset/quality.py`

Inclui:

- `AssetQualityProfile`;
- `AssetQualityPolicy`;
- `AssetQualityCheck`;
- `AssetQualityAssessment`;
- `assess_asset_quality`.

Regras principais:

- o motor não inventa fundamento;
- qualidade precisa ser fornecida explicitamente;
- ativo inelegível para exercício falha;
- ativo inadequado para longo prazo falha;
- qualidade abaixo do mínimo falha;
- qualidade aceitável mas não forte vira atenção;
- concentração acima do limite falha quando informada;
- confiança dos dados é separada da qualidade.

### `engine/strategy/put.py`

Inclui:

- `PutStrategyConfig`;
- `StrategyCheck`;
- `PutStrategyEvaluation`;
- `evaluate_put_strategy`.

A avaliação combina:

- oportunidade;
- métricas de PUT;
- filtros de segurança;
- qualidade do ativo.

Estados possíveis:

- `eligible`;
- `watchlist`;
- `ineligible`;
- `insufficient_data`.

Regra crítica:

> Prêmio alto ou ROI alto não resgata ativo inelegível.

---

## Testes

Foram criados:

- `tests/test_engine_asset_quality.py`;
- `tests/test_engine_put_strategy.py`.

Validação local da Sprint C:

```text
Ran 12 tests
OK
```

Cobertura nova:

- ativo aprovado para exercício;
- ativo inelegível bloqueia operação;
- qualidade ausente gera dados insuficientes;
- qualidade aceitável mas fraca gera atenção;
- concentração acima do limite falha;
- ratio inválido é rejeitado;
- PUT elegível quando segurança e ativo passam;
- PUT de ativo ruim falha mesmo com prêmio alto;
- filtro de segurança falho bloqueia estratégia;
- desconto baixo vira watchlist;
- mismatch entre ativo da PUT e avaliação do ativo é rejeitado.

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
- Score IA;
- ranking;
- Radar visual.

---

## Comparação com `main`

Antes deste relatório:

- branch à frente de `main`;
- `ahead_by: 7`;
- `behind_by: 0`;
- alterações restritas a `engine/` e `tests/`.

Após este relatório, o diff inclui também:

```text
docs/SPRINT_FUNCIONAL_C.md
```

---

## Resultado

A Sprint C transforma o Decision Engine em um avaliador mais coerente com a estratégia oficial:

- primeiro qualidade do ativo;
- depois segurança;
- depois preço líquido e retorno;
- sem deixar prêmio alto mascarar risco real.

O próximo passo natural após esta Sprint é a Sprint Funcional D — Score IA explicável.
