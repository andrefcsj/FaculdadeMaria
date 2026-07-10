# Relatório Técnico — Sprint Funcional B

## Status

- Sprint: `Funcional B — Indicadores e Segurança`.
- Issue: `#19`.
- Product Owner: Andre.
- Branch: `sprint-funcional-b-indicators-safety`.
- Base oficial: `main` no commit `c42bee6b9927e26a2b2bfcb00d1d042a688dab59`.
- Natureza: segunda evolução funcional do novo Decision Engine.
- Merge: não realizado neste relatório.
- Alteração visual: nenhuma.

---

## Objetivo

Implementar a segunda camada funcional do novo `engine/`, cobrindo:

- `FM-ENG-020` — indicadores técnicos puros;
- `FM-RISK-010` — filtros mínimos de segurança;
- `FM-RISK-030` — distância do strike ajustada por ATR.

A Sprint preserva integralmente:

- Flask;
- rotas;
- templates;
- CSS;
- JavaScript;
- banco;
- CSV;
- persistência;
- `motor_ia/` legado;
- Score IA;
- ranking;
- Radar.

---

## Implementado

### Indicadores técnicos

Criado:

```text
engine/indicators/technical.py
engine/indicators/__init__.py
```

Funções públicas:

- `simple_moving_average`;
- `moving_average_21`;
- `moving_average_200`;
- `relative_strength_index`;
- `bollinger_bands`;
- `true_range`;
- `average_true_range`;
- `historical_volatility`;
- `strike_distance_in_atr`.

Estrutura pública:

- `BollingerBands`.

Características:

- funções puras;
- sem rede;
- sem provider;
- sem banco;
- sem CSV;
- uso de `Decimal`;
- tratamento de histórico insuficiente com `None`;
- erros estruturados para entrada inválida.

### Filtros mínimos de segurança

Criado:

```text
engine/filters/safety.py
engine/filters/__init__.py
```

API pública:

- `SafetyFilterConfig`;
- `SafetyCheck`;
- `SafetyEvaluation`;
- `evaluate_put_safety`.

Status possíveis:

- `passed`;
- `attention`;
- `failed`.

Checks implementados:

- dado obrigatório ausente;
- liquidez mínima;
- liquidez ausente;
- spread bid/ask máximo;
- spread não avaliável;
- PUT com strike acima do spot quando não permitido;
- ROI bruto mínimo;
- DTE mínimo;
- DTE máximo;
- métricas ausentes quando necessárias.

### API pública

Atualizado:

```text
engine/__init__.py
```

Novos exports públicos:

- indicadores técnicos;
- `BollingerBands`;
- `SafetyFilterConfig`;
- `SafetyEvaluation`;
- `evaluate_put_safety`.

---

## Arquivos criados

- `engine/indicators/__init__.py`;
- `engine/indicators/technical.py`;
- `engine/filters/__init__.py`;
- `engine/filters/safety.py`;
- `tests/test_engine_indicators.py`;
- `tests/test_engine_safety_filters.py`;
- `docs/SPRINT_FUNCIONAL_B.md`.

## Arquivos modificados

- `engine/__init__.py`.

---

## Testes

A tentativa de `git clone` no sandbox falhou por DNS:

```text
Could not resolve host: github.com
```

Validação alternativa segura executada localmente com os arquivos publicados/reconstruídos da Sprint B:

```text
Ran 16 tests
OK
```

Resumo da validação nova:

- 16 testes executados;
- 16 aprovados;
- 0 falhas;
- 0 erros.

Cobertura nova:

- média móvel simples;
- MM21;
- MM200;
- RSI/IFR;
- Bollinger;
- True Range;
- ATR;
- volatilidade histórica;
- distância do strike em ATR;
- histórico insuficiente;
- entrada inválida;
- safety check aprovado;
- dado obrigatório ausente;
- liquidez ausente;
- liquidez insuficiente;
- spread excessivo;
- ROI mínimo;
- DTE mínimo e máximo;
- strike de PUT acima do spot;
- métricas ausentes;
- configuração inválida.

---

## Comparação com `main`

Comparação executada:

```text
base: main
head: sprint-funcional-b-indicators-safety
```

Resultado antes deste relatório:

- branch à frente;
- `ahead_by: 7`;
- `behind_by: 0`;
- 7 arquivos alterados;
- alterações restritas a `engine/` e `tests/`.

Após este relatório, o diff inclui também:

```text
docs/SPRINT_FUNCIONAL_B.md
```

---

## Escopo não executado

Não implementado nesta Sprint:

- Score IA;
- ranking;
- qualidade do ativo;
- avaliador completo de PUT;
- provider real;
- rede;
- banco;
- CSV;
- Flask;
- rotas;
- templates;
- CSS;
- JavaScript;
- Radar visual;
- rolagem;
- Machine Learning.

---

## Conclusão

A Sprint Funcional B adiciona a primeira camada de leitura técnica e segurança determinística ao Decision Engine.

O motor passa a possuir indicadores técnicos puros e filtros mínimos de segurança, mas ainda não decide, ranqueia ou recomenda operação.

Nenhuma funcionalidade existente foi alterada.

O próximo passo natural, após revisão e eventual merge, é a Sprint Funcional C — Qualidade do Ativo e Estratégia PUT.
