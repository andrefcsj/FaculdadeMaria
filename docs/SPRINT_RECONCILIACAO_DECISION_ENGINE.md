# Relatório Técnico — Reconciliação da Especificação do Decision Engine

## 1. Status

- Natureza: correção documental e arquitetural.
- Product Owner: Andre.
- Issue: `#13 — Reconciliação documental — especificação e roadmap do Decision Engine`.
- Branch: `docs-reconciliacao-decision-engine`.
- Base oficial: `main` no commit `f2425862c95f290f626eeb5af47dd88eb7482573`.
- Alteração funcional: nenhuma.
- Sprint Funcional A: não iniciada.
- Merge: não realizado neste relatório.

---

## 2. Objetivo

Reconciliar documentos técnicos antigos com:

- estratégia operacional oficial;
- Product Vision;
- backlog oficial;
- regras permanentes;
- arquitetura pós-Sprint 1.1-R;
- código real da `main`.

A correção prepara o projeto para iniciar futuramente a Sprint Funcional A sem ambiguidade sobre:

- caminho oficial do motor;
- elegibilidade;
- Score IA;
- ranking;
- confiança dos dados;
- prioridade de venda de PUT.

---

## 3. Leitura e auditoria obrigatórias

Antes da alteração foram lidos integralmente os documentos oficiais conhecidos em `docs/`:

- `ARQUITETURA_V4.md`;
- `DECISION_ENGINE_SPEC.md`;
- `ROADMAP_V5.md`;
- `ESTRATEGIA_OPERACIONAL.md`;
- `PRODUCT_VISION.md`;
- `BACKLOG.md`;
- `REGRAS_DO_PROJETO.md`;
- `CHANGELOG_DESENVOLVIMENTO.md`;
- `SPRINT_01.md`;
- `SPRINT_01_R.md`;
- `SPRINT_01_R_ENCERRAMENTO.md`;
- `SPRINT_DOCS_ESTRATEGIA_OPERACIONAL.md`;
- `SPRINT_ORGANIZACAO_OFICIAL.md`.

Também foram conferidos no código real da `main`:

- `engine/__init__.py`;
- `engine/errors.py`;
- `engine/telemetry.py`;
- `engine/version.py`;
- `engine/core/__init__.py`;
- `engine/core/context.py`;
- `engine/core/pipeline.py`;
- `engine/providers/__init__.py`;
- `engine/providers/base.py`.

Conclusão da auditoria do código:

- fundação do `engine/` coerente;
- pipeline pass-through;
- nenhum Score funcional;
- nenhum ranking funcional;
- nenhum indicador funcional;
- provider abstrato;
- versão interna `1.1.0`;
- nenhuma integração Flask/Radar.

---

## 4. Divergências encontradas

### 4.1 Ranking antigo

`DECISION_ENGINE_SPEC.md` ainda definia ordem centrada em:

1. Score;
2. classe;
3. liquidez;
4. ROI;
5. distância do strike;
6. DTE;
7. confiança.

Essa ordem conflitava com a prioridade oficial:

1. qualidade do ativo;
2. segurança;
3. preço líquido;
4. risco x retorno;
5. eficiência do capital;
6. liquidez;
7. probabilidade de exercício;
8. prêmio.

### 4.2 Legado `motor_ia/` no roadmap

`ROADMAP_V5.md` ainda previa:

- corrigir o contrato do `motor_ia/`;
- integrar `motor_ia/` ao Radar.

Isso conflitava com o estado oficial:

- `engine/` é o novo caminho do Decision Engine;
- `motor_ia/` é legado isolado.

### 4.3 Ordem histórica de implementação

`SPRINT_01_R.md` preserva recomendação histórica de:

- indicadores e filtros primeiro;
- Score e ranking depois.

O backlog vigente passou a priorizar:

1. contratos completos;
2. métricas de PUT;
3. normalização;
4. indicadores;
5. qualidade do ativo;
6. segurança;
7. avaliador de PUT;
8. Score;
9. ranking;
10. serviço de Radar;
11. Radar Premium.

---

## 5. Decisão sobre documentos históricos

`SPRINT_01_R.md` não foi reescrito.

Motivo:

- é relatório histórico;
- registra corretamente a recomendação existente naquele momento;
- modificar o passado reduziria qualidade de auditoria.

A especificação e o roadmap vigentes passam a declarar explicitamente que:

- o backlog oficial define a ordem atual;
- orientações históricas conflitantes não possuem precedência sobre os documentos vigentes.

Essa abordagem preserva história sem manter ambiguidade operacional.

---

## 6. Arquivos modificados

### 6.1 `docs/DECISION_ENGINE_SPEC.md`

Foi reconciliado para formalizar:

- prioridade inicial de venda de PUT;
- exercício não tratado como falha automática;
- hierarquia oficial de decisão;
- qualidade antes de prêmio;
- preço líquido como eixo central;
- gates de elegibilidade;
- Score incapaz de resgatar operação inelegível;
- confiança dos dados separada da oportunidade;
- ranking somente após elegibilidade;
- ranking ajustado ao perfil;
- caminho crítico A–F;
- `engine/` como caminho oficial;
- `motor_ia/` como legado isolado;
- contratos conceituais de entrada e saída;
- métricas operacionais de PUT;
- regras de rolagem futura;
- princípios de testabilidade e falhas.

### 6.2 `docs/ROADMAP_V5.md`

Foi reconciliado para:

- remover integração planejada do legado `motor_ia/`;
- reconhecer `engine/` como motor oficial;
- separar Trilha A de Decision Engine/Radar e Trilha B de modernização do Flask;
- formalizar Sprints Funcionais A–F;
- preservar objetivos válidos de serviços, repositórios, rotas, dashboard, backup e produção;
- impedir associação automática de número de versão a funcionalidade ainda não autorizada.

### 6.3 `docs/CHANGELOG_DESENVOLVIMENTO.md`

Foi atualizado para registrar:

- Issue #13;
- divergências encontradas;
- decisões de reconciliação;
- preservação do código funcional.

---

## 7. Arquivos criados

- `docs/SPRINT_RECONCILIACAO_DECISION_ENGINE.md`.

---

## 8. Decisões arquiteturais

### 8.1 Gates antes do Score

Critério crítico pode tornar uma oportunidade inelegível.

Regra:

> Score IA não pode resgatar oportunidade que falhou em gate obrigatório.

### 8.2 Ranking após elegibilidade

O ranking não mistura indiscriminadamente:

- elegível;
- observação;
- inelegível;
- dados insuficientes.

A ordenação principal ocorre após avaliação de elegibilidade.

### 8.3 Confiança separada

Oportunidade e confiança são dimensões diferentes.

Exemplo:

- oportunidade boa + dado confiável;
- oportunidade boa + dado incompleto;

não podem receber a mesma interpretação.

### 8.4 `engine/` oficial

O novo Decision Engine evolui em `engine/`.

O legado `motor_ia/` permanece isolado.

### 8.5 PUT como prioridade inicial

CALL coberta e Wheel permanecem compatíveis com futuro arquitetural, mas não precedem a estratégia operacional atual.

---

## 9. Testes executados

Comando oficial:

```bash
python -m unittest discover -s tests -v
```

Como o `git clone` falhou por resolução DNS do sandbox, a suíte foi reconstruída localmente usando os arquivos exatos lidos da `main` pelo conector GitHub.

Resultado:

```text
Ran 7 tests in 0.002s
OK
```

Resumo:

- 7 executados;
- 7 aprovados;
- 0 falhas;
- 0 erros.

Cobertura:

- pipeline pass-through;
- versão centralizada;
- contexto e traces;
- imports proibidos;
- erros estruturados;
- hierarquia de provider;
- telemetria.

---

## 10. Comparação com `main`

Base:

```text
f2425862c95f290f626eeb5af47dd88eb7482573
```

Estado antes da criação deste relatório:

- branch `ahead`;
- `ahead_by: 3`;
- `behind_by: 0`;
- três arquivos alterados;
- todos em `docs/`.

Após este relatório, o diff inclui também:

- `docs/SPRINT_RECONCILIACAO_DECISION_ENGINE.md`.

---

## 11. Ausência de regressões

Confirmado pelo escopo e pela comparação:

- nenhum arquivo Python alterado;
- `engine/` inalterado;
- `motor_ia/` inalterado;
- Flask inalterado;
- `app.py` inalterado;
- rotas inalteradas;
- templates inalterados;
- CSS inalterado;
- JavaScript inalterado;
- banco inalterado;
- CSV inalterado;
- persistência inalterada;
- comportamento funcional inalterado.

---

## 12. Escopo executado

Executado:

- leitura integral da documentação oficial conhecida;
- comparação documentação x documentação;
- comparação documentação x código;
- reconciliação da especificação;
- reconciliação do roadmap;
- atualização do changelog;
- formalização de gates;
- formalização de ranking pós-elegibilidade;
- separação de confiança;
- preservação histórica;
- regressão;
- comparação com `main`;
- relatório técnico.

---

## 13. Escopo não executado

Não executado:

- contratos funcionais;
- métricas funcionais de PUT;
- indicadores;
- qualidade do ativo funcional;
- filtros funcionais;
- Score funcional;
- ranking funcional;
- provider real;
- integração Flask;
- serviço de Radar;
- rota de Radar;
- template;
- CSS;
- JavaScript;
- Radar Premium;
- rolagem funcional;
- Machine Learning;
- alteração de `motor_ia/`.

A Sprint Funcional A não foi iniciada.

---

## 14. Riscos e mitigação

### Risco: Score mascarar falha crítica

Mitigação:

- gates obrigatórios;
- Score posterior à elegibilidade.

### Risco: confiança ser confundida com qualidade

Mitigação:

- dimensões separadas.

### Risco: roadmap reativar legado

Mitigação:

- `engine/` declarado caminho oficial;
- `motor_ia/` declarado legado isolado.

### Risco: histórico induzir ordem errada

Mitigação:

- documentos vigentes declaram precedência do backlog;
- relatório histórico preservado sem reescrever o passado.

---

## 15. Pendências

Permanecem para Sprints futuras autorizadas:

- `FM-ENG-010`;
- `FM-PUT-010`;
- `FM-DATA-010`;
- `FM-ENG-020`;
- `FM-ASSET-010`;
- `FM-RISK-010`;
- `FM-PUT-020`;
- `FM-SCORE-010`;
- `FM-EXPLAIN-010`;
- `FM-RANK-010`;
- `FM-SVC-010`;
- `FM-UI-010`.

---

## 16. Conclusão

A documentação técnica passa a convergir para uma única filosofia:

- `engine/` é o novo motor oficial;
- venda de PUT é a prioridade operacional inicial;
- exercício não é falha automática;
- qualidade e segurança precedem prêmio;
- preço líquido é central;
- Score não resgata inelegibilidade;
- confiança é separada da qualidade;
- ranking respeita perfil operacional;
- o caminho até o Radar Premium segue o backlog oficial.

Nenhuma funcionalidade existente foi alterada.

A Sprint Funcional A permanece não iniciada.

O próximo passo, após revisão e eventual merge autorizado desta correção documental, é preparar a Sprint Funcional A sobre uma base de especificação coerente.