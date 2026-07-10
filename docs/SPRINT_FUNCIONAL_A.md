# Relatório Técnico — Sprint Funcional A

## 1. Status

- Sprint: `Funcional A — Contratos e Métricas de PUT`.
- Issue: `#16`.
- Product Owner: Andre.
- Branch: `sprint-funcional-a-put-contracts-metrics`.
- Base oficial: `main` no commit `af051c65ea9abee39b912d7428a0f1eb93395cdd`.
- Natureza: primeira evolução funcional do novo Decision Engine.
- Merge: não realizado neste relatório.
- Sprint seguinte: não iniciada.

---

## 2. Objetivo

Implementar a primeira camada funcional do novo `engine/`, cobrindo:

- `FM-ENG-010` — contrato completo de oportunidade;
- `FM-PUT-010` — métricas operacionais de PUT;
- parte de `FM-DATA-010` — normalização mínima e rastreável de dados de mercado.

A Sprint preserva integralmente:

- Flask;
- rotas;
- templates;
- CSS;
- JavaScript;
- banco;
- CSV;
- persistência;
- `motor_ia/` legado.

---

## 3. Auditoria obrigatória anterior à implementação

Antes do primeiro código foram lidos integralmente os documentos oficiais aplicáveis em `docs/` e comparados com o código real da `main`.

Foram confirmados:

- `engine/` como caminho oficial do novo Decision Engine;
- `motor_ia/` como legado isolado;
- prioridade operacional de venda sistemática de PUT;
- preço líquido como eixo central;
- confiança dos dados separada da qualidade da oportunidade;
- Sprint Funcional A como próximo passo vigente;
- ausência de divergência entre documentação e código.

Código-base conferido:

- `engine/__init__.py`;
- `engine/errors.py`;
- `engine/telemetry.py`;
- `engine/version.py`;
- `engine/core/__init__.py`;
- `engine/core/context.py`;
- `engine/core/pipeline.py`;
- `engine/providers/__init__.py`;
- `engine/providers/base.py`.

---

## 4. Escopo implementado

### 4.1 Contrato de oportunidade

Criado:

```text
engine/core/contracts.py
```

Contrato principal:

```text
OptionOpportunity
```

Campos:

- `asset`;
- `option_code`;
- `option_type`;
- `expiry`;
- `spot_price`;
- `strike`;
- `premium`;
- `bid`;
- `ask`;
- `volume`;
- `trades`;
- `liquidity`;
- `implied_volatility`;
- `timestamp`;
- `source`;
- `data_confidence`.

Regras principais:

- contrato imutável;
- `PUT` e `CALL` canonicalizados;
- datas explícitas;
- valores monetários e razões em `Decimal`;
- preço spot e strike positivos quando informados;
- prêmio, bid, ask, liquidez e IV não negativos quando informados;
- volume e negócios inteiros não negativos;
- `ask` não pode ser menor que `bid`;
- timestamp deve possuir timezone;
- confiança deve estar entre 0 e 1;
- dados ausentes permanecem `None`;
- zero explícito permanece zero;
- campos ausentes são rastreáveis por `missing_fields()`;
- campos obrigatórios por cálculo podem ser exigidos com `require_fields()`.

### 4.2 Snapshot normalizado

Criados:

```text
engine/market/snapshot.py
engine/market/normalizer.py
engine/market/__init__.py
```

Estrutura:

```text
NormalizedMarketSnapshot
```

Capacidades:

- normalização numérica;
- suporte a decimal com ponto;
- suporte a decimal com vírgula;
- tratamento controlado de ponto e vírgula combinados;
- normalização de inteiros;
- datas ISO;
- datas `DD/MM/YYYY`;
- timestamp ISO-8601;
- conversão de timestamp para UTC;
- rejeição de timestamp sem timezone;
- preservação da fonte;
- preservação da confiança;
- identificação explícita de campos ausentes;
- distinção entre `None` e zero.

Nenhum provider real foi implementado.

### 4.3 Métricas operacionais de PUT

Criados:

```text
engine/metrics/options.py
engine/metrics/__init__.py
```

API principal:

```text
PutMetricAssumptions
PutMetrics
calculate_put_metrics
```

Métricas implementadas:

- preço líquido de aquisição;
- desconto em relação ao mercado;
- ROI bruto;
- ROI líquido quando custos explícitos existem;
- ROI anualizado;
- ROI líquido anualizado quando aplicável;
- distância percentual do strike;
- dias até vencimento;
- retorno por dia;
- prêmio bruto total;
- prêmio líquido total quando custos explícitos existem;
- capital nominal comprometido;
- eficiência do capital;
- retorno sobre margem quando margem real é informada.

---

## 5. Fórmulas e convenções oficiais desta Sprint

### 5.1 Preço líquido de aquisição

```text
preco_liquido = strike - premio
```

### 5.2 Desconto em relação ao mercado

```text
desconto_mercado = (spot - preco_liquido) / spot
```

### 5.3 Capital nominal cash-secured

```text
capital_nominal = strike * contract_size
```

`contract_size` é explícito.

O padrão é:

```text
contract_size = 1
```

Isso significa cálculo por unidade e evita inventar lote padrão da B3.

### 5.4 Prêmio bruto total

```text
premio_bruto_total = premio * contract_size
```

### 5.5 ROI bruto

```text
roi_bruto = premio_bruto_total / capital_nominal
```

Base:

```text
nominal_cash_secured
```

### 5.6 ROI líquido

Só existe quando `costs_total` é explicitamente informado.

```text
premio_liquido_total = premio_bruto_total - costs_total
roi_liquido = premio_liquido_total / capital_nominal
```

Sem custo explícito:

```text
roi_liquido = None
```

O motor não inventa corretagem, emolumentos, impostos ou qualquer outro custo.

### 5.7 Distância percentual do strike

Para PUT:

```text
distancia_strike = (spot - strike) / spot
```

Valor positivo indica strike abaixo do spot.

### 5.8 DTE

```text
dte = expiry - as_of_date
```

- vencimento passado gera erro;
- DTE zero é permitido;
- DTE zero não é anualizado.

### 5.9 ROI anualizado

Convenção desta Sprint:

```text
anualizacao_simples = roi * annualization_days / dte
```

Padrão:

```text
annualization_days = 365
annualization_method = simple
```

A convenção é exposta na saída para evitar precisão fictícia.

### 5.10 Retorno por dia

Quando DTE > 0:

```text
retorno_por_dia = roi_bruto / dte
```

### 5.11 Eficiência do capital

Quando `committed_capital` é explicitamente informado:

```text
eficiencia_capital = premio_bruto_total / committed_capital
capital_basis = explicit_committed_capital
```

Quando não é informado:

```text
eficiencia_capital = premio_bruto_total / capital_nominal
capital_basis = nominal_cash_secured
```

A base utilizada é exposta na saída.

### 5.12 Retorno sobre margem

Só existe quando `real_margin` é explicitamente informada:

```text
retorno_margem = premio_bruto_total / real_margin
```

Sem margem real:

```text
retorno_margem = None
```

O motor não estima margem como fato.

---

## 6. Decisões de segurança financeira

### 6.1 Decimal em vez de float

Os contratos e métricas usam:

```text
Decimal
```

Objetivo:

- reduzir ruído binário de ponto flutuante;
- aumentar reproduzibilidade;
- evitar arredondamento escondido no domínio.

A apresentação futura será responsável por formatação.

### 6.2 Ausência não é zero

Regra:

```text
None != 0
```

Exemplos:

- volume ausente não vira zero;
- liquidez ausente não vira zero;
- custo ausente não vira zero;
- margem ausente não vira zero;
- IV ausente não vira zero.

### 6.3 Custos nunca inventados

Sem custo explícito:

- ROI bruto existe;
- ROI líquido fica indisponível.

### 6.4 Margem nunca inventada

Sem margem real:

- retorno sobre margem fica indisponível.

### 6.5 Lote nunca inventado

A Sprint não assume automaticamente lote de 100.

O multiplicador é explícito por `contract_size`.

### 6.6 Anualização transparente

A saída informa:

- método;
- dias por ano;
- DTE.

DTE zero não produz anualização enganosa.

---

## 7. API pública atualizada

Atualizados:

```text
engine/__init__.py
engine/core/__init__.py
```

Novos exports públicos:

```text
OptionOpportunity
PutMetricAssumptions
PutMetrics
calculate_put_metrics
```

A API antiga foi preservada:

```text
DecisionEngineError
ENGINE_VERSION
get_engine_version
DecisionContext
DecisionPipeline
run_pipeline
```

---

## 8. Arquivos criados

### Engine

- `engine/core/contracts.py`;
- `engine/market/__init__.py`;
- `engine/market/normalizer.py`;
- `engine/market/snapshot.py`;
- `engine/metrics/__init__.py`;
- `engine/metrics/options.py`.

### Testes

- `tests/test_engine_contracts.py`;
- `tests/test_engine_market_normalizer.py`;
- `tests/test_engine_put_metrics.py`.

### Documentação

- `docs/SPRINT_FUNCIONAL_A.md`.

---

## 9. Arquivos modificados

- `engine/__init__.py`;
- `engine/core/__init__.py`.

---

## 10. Testes executados

Comando:

```bash
python -m unittest discover -s tests -v
```

Resultado final da implementação antes deste relatório:

```text
Ran 21 tests in 0.005s
OK
```

Resumo:

- 21 executados;
- 21 aprovados;
- 0 falhas;
- 0 erros.

Cobertura adicional da Sprint:

- contrato válido;
- canonicalização de PUT;
- zero explícito;
- campos ausentes;
- tipo de opção inválido;
- timestamp sem timezone;
- decimal com vírgula;
- data brasileira;
- normalização para UTC;
- valor booleano rejeitado como número;
- preço líquido;
- desconto ao mercado;
- ROI bruto;
- ROI líquido;
- anualização;
- distância do strike;
- DTE;
- capital nominal;
- eficiência de capital;
- retorno sobre margem;
- custos ausentes;
- margem ausente;
- vencimento expirado;
- campo obrigatório ausente;
- CALL rejeitada no cálculo de PUT;
- premissas inválidas;
- mesma entrada produz mesma saída;
- regressão dos testes anteriores;
- ausência de imports proibidos.

---

## 11. Teste funcional controlado

Entrada:

```text
ativo = PETR4
opcao = PETRT280
tipo = PUT
spot = 30.00
strike = 28.00
premio = 1.40
vencimento = 2026-08-21
as_of_date = 2026-07-10
contract_size = 100
```

Saída principal observada:

```text
preco_liquido = 26.60
roi_bruto = 0.05
dte = 42
capital_nominal = 2800
roi_anualizado_simples = 0.4345238095238095238095238095
```

O teste foi executado localmente sobre o mesmo conteúdo implementado e publicado na branch.

---

## 12. Comparação com `main`

Base:

```text
af051c65ea9abee39b912d7428a0f1eb93395cdd
```

Antes deste relatório, a comparação confirmou:

- branch `ahead`;
- `ahead_by: 12`;
- `behind_by: 0`;
- 11 arquivos alterados;
- alterações restritas a `engine/` e `tests/`;
- nenhum arquivo Flask alterado;
- nenhum arquivo de interface alterado;
- nenhuma persistência alterada.

Após este relatório, o diff inclui também:

```text
docs/SPRINT_FUNCIONAL_A.md
```

---

## 13. Ausência de regressões

Preservados:

- `app.py`;
- Flask;
- rotas;
- URLs;
- templates;
- CSS;
- JavaScript;
- dashboard;
- operações abertas;
- operações fechadas;
- histórico;
- desempenho;
- configurações;
- backup;
- exportações;
- PostgreSQL;
- SQLite;
- CSV;
- pasta `data/`;
- `motor_ia/`;
- providers reais existentes fora do novo motor.

A pipeline atual continua pass-through.

Nenhum Score foi implementado.

Nenhum ranking foi implementado.

Nenhum filtro de segurança foi implementado.

Nenhuma qualidade de ativo foi implementada.

Nenhuma integração Flask/Radar foi implementada.

---

## 14. Escopo executado

Executado:

- contrato de oportunidade;
- validação determinística;
- rastreabilidade de campos ausentes;
- normalização mínima de mercado;
- preservação de fonte e timestamp;
- distinção entre ausência e zero;
- métricas operacionais de PUT;
- premissas explícitas;
- API pública;
- testes próprios;
- regressão;
- teste funcional controlado;
- comparação com `main`;
- relatório técnico.

---

## 15. Escopo não executado

Não executado:

- provider real;
- rede;
- banco;
- CSV;
- persistência;
- indicador técnico;
- MM21;
- MM200;
- IFR14;
- Bollinger;
- ATR;
- qualidade do ativo;
- gate de segurança funcional;
- Score IA;
- nota 0 a 10;
- ranking;
- explicação final;
- serviço de Radar;
- rota de Radar;
- template;
- CSS;
- JavaScript;
- Radar Premium;
- rolagem funcional;
- Machine Learning;
- alteração de `motor_ia/`.

---

## 16. Riscos e mitigação

### 16.1 Fórmula de ROI ambígua

Mitigação:

- ROI bruto usa base nominal cash-secured explícita;
- capital basis é exposta;
- margem possui métrica separada.

### 16.2 Anualização enganosa

Mitigação:

- método simples declarado;
- base 365 declarada;
- DTE exposto;
- DTE zero retorna anualização indisponível.

### 16.3 Precisão fictícia de custos

Mitigação:

- custo ausente produz ROI líquido indisponível.

### 16.4 Margem inventada

Mitigação:

- retorno sobre margem só existe com `real_margin` explícita.

### 16.5 Lote B3 presumido

Mitigação:

- padrão por unidade;
- `contract_size` explícito.

### 16.6 Dado ausente virar zero

Mitigação:

- `None` preservado;
- missing fields rastreáveis;
- zero explícito preservado.

---

## 17. Pendências futuras

Permanecem fora desta Sprint:

- conclusão integral de `FM-DATA-010`;
- `FM-ENG-020`;
- `FM-ASSET-010`;
- `FM-RISK-010`;
- `FM-RISK-030`;
- `FM-PUT-020`;
- `FM-CAP-010`;
- `FM-SCORE-010`;
- `FM-EXPLAIN-010`;
- `FM-RANK-010`;
- `FM-SVC-010`;
- `FM-UI-010`.

---

## 18. Conclusão

A Sprint Funcional A implementa a primeira inteligência operacional real do novo Decision Engine.

O motor passa a possuir:

- contrato estável de oportunidade;
- dados ausentes explícitos;
- normalização mínima independente de provider;
- cálculo auditável de preço líquido;
- desconto ao mercado;
- ROI bruto;
- ROI líquido condicionado a custo real;
- ROI anualizado com convenção explícita;
- distância do strike;
- DTE;
- capital nominal;
- eficiência do capital;
- retorno sobre margem somente com margem real;
- testes determinísticos.

Nenhuma funcionalidade existente foi alterada.

A Sprint seguinte não foi iniciada.

O próximo passo é revisão do Product Owner e autorização explícita antes de qualquer merge.
