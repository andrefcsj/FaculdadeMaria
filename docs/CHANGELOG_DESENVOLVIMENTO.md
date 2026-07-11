# Changelog de Desenvolvimento — FaculdadeMaria

## 1. Status

Este documento registra mudanças relevantes de desenvolvimento, arquitetura, governança e produto do FaculdadeMaria.

Ele não substitui:

- histórico do Git;
- Pull Requests;
- Issues;
- relatórios técnicos de Sprint.

Seu objetivo é oferecer uma visão cronológica e legível da evolução oficial do projeto.

---

## 2. Convenções

Categorias utilizadas:

- `Added`: adicionado;
- `Changed`: alterado;
- `Fixed`: corrigido;
- `Validated`: validado;
- `Deprecated`: marcado como legado;
- `Security`: segurança ou integridade;
- `Docs`: documentação e governança.

Somente mudanças integradas à `main` são estado vigente.

Mudanças ainda em branch podem aparecer como `Em revisão`.

---

## 2026-07-11 — Dashboard Executivo Premium

Status: `Em revisão`

Branch:

```text
agent/dashboard-executivo-premium
```

### Fixed

- reconciliado o estado oficial da arquitetura com as Sprints A–I já integradas;
- corrigido o status de merge dos providers B3/CVM e dos cards Premium do Radar.

### Changed

- Dashboard reorganizado no padrão Executive aprovado pelo Product Owner;
- menu lateral reorganizado por Visão Geral, Inteligência, Operações, Gestão e Sistema;
- dados existentes apresentados em componentes reutilizáveis, sem métricas fictícias;
- estados vazios explícitos para oportunidades que dependem do Radar atualizado.

### Added

- adaptador de apresentação do Dashboard;
- Resumo Executivo da IA;
- composição da carteira;
- visão de rolagem, atenção, vencimentos, metas e estatísticas rápidas;
- testes do novo adaptador.

---

## 2026-07-10 — Reconciliação da especificação e roadmap do Decision Engine

Status: `Integrado`

Issue: `#13` — encerrada como `completed`

Pull Request: `#14`

Commit de merge:

```text
793bd4ea9007949eb1bcf89f819316dc3a9d0d83
```

Branch de origem:

```text
docs-reconciliacao-decision-engine
```

### Fixed

Foram reconciliadas divergências entre documentos antigos e a política operacional vigente:

- ranking antigo centrado em Score, classe, liquidez e ROI;
- roadmap antigo ainda orientado à integração do legado `motor_ia/`;
- recomendações históricas de ordem de implementação superadas pelo backlog oficial.

### Changed

- `docs/DECISION_ENGINE_SPEC.md` passa a refletir a estratégia operacional oficial;
- `docs/ROADMAP_V5.md` passa a reconhecer `engine/` como único caminho oficial do novo motor;
- gates de elegibilidade passam a preceder Score e ranking;
- Score IA não pode resgatar oportunidade inelegível;
- confiança dos dados passa a ser dimensão separada da qualidade da oportunidade;
- ranking passa a ser ajustado ao perfil operacional;
- caminho vigente até o Radar Premium passa a seguir o backlog e as Sprints Funcionais A–F.

### Preserved

- nenhum código funcional alterado;
- `engine/` inalterado;
- `motor_ia/` inalterado;
- Flask inalterado;
- interface inalterada;
- persistência inalterada.

### Validated

- 7 testes executados;
- 7 aprovados;
- 0 falhas;
- 0 erros;
- diff pré-merge restrito a `docs/`.

---

## 2026-07-10 — Sincronização pós-merge da Organização Oficial

Status: `Integrado`

Issue: `#10`

Pull Request: `#12`

Commit de merge:

```text
f2425862c95f290f626eeb5af47dd88eb7482573
```

### Docs

- sincronizado `docs/SPRINT_ORGANIZACAO_OFICIAL.md` com o estado real pós-merge;
- registrado o merge do PR #6;
- registrado o merge do PR #8;
- registrado o encerramento das Issues #5 e #7 como `completed`;
- consolidado o estado oficial da `main` após a Organização Oficial.

### Validated

- regressão pós-merge executada;
- 7 testes aprovados;
- 0 falhas;
- 0 erros;
- diff da sincronização restrito à documentação.

---

## 2026-07-10 — Sprint de Organização Oficial

Status: `Integrado`

Issue: `#7` — encerrada como `completed`

Pull Request: `#8`

Commit de merge:

```text
c76fb448490141c45121bfa71a1c25b441daf169
```

### Added

- `docs/PRODUCT_VISION.md`;
- `docs/BACKLOG.md`;
- `docs/REGRAS_DO_PROJETO.md`;
- `docs/CHANGELOG_DESENVOLVIMENTO.md`;
- `docs/SPRINT_ORGANIZACAO_OFICIAL.md`.

### Changed

- `docs/ARQUITETURA_V4.md` passou a reconhecer visão, backlog, regras e changelog oficiais;
- `docs/ESTRATEGIA_OPERACIONAL.md` passou a apontar para o backlog oficial;
- formalizado o caminho crítico até o Radar Premium;
- formalizadas prioridades `P0` a `P3`;
- criados identificadores oficiais de backlog;
- consolidadas regras permanentes do projeto.

### Direção de produto

Foi registrado como primeiro grande resultado visual futuro:

- Radar Premium;
- Score IA explicável;
- preço líquido;
- ROI bruto, líquido e anualizado;
- risco;
- liquidez;
- distância do strike;
- pontos positivos;
- pontos de atenção;
- conclusão técnica.

### Validated

- diff da Sprint restrito a `docs/`;
- 7 testes aprovados;
- nenhuma regressão funcional;
- PR revalidado como mergeável após retarget para `main`.

---

## 2026-07-10 — Correção documental pós-merge da Estratégia Operacional

Status: `Integrado`

Issue: `#5` — encerrada como `completed`

Pull Request: `#6`

Commit de merge:

```text
2edecb8b3bc2d514733b68b7519bd5433819bfaf
```

### Fixed

- sincronização de `docs/SPRINT_DOCS_ESTRATEGIA_OPERACIONAL.md` com o estado real pós-merge;
- registro do PR #4 como mergeado;
- registro do commit de merge `7ee1a5a6598182bd1ba313c1e582dc036e1d3614`;
- registro da Issue #3 como encerrada.

### Validated

- diff líquido restrito ao relatório documental;
- 7 testes aprovados;
- nenhuma regressão funcional.

---

## 2026-07-10 — Estratégia Operacional e Reconciliação Arquitetural

Status: `Integrado`

Issue: `#3`

Pull Request: `#4`

Commit de merge:

```text
7ee1a5a6598182bd1ba313c1e582dc036e1d3614
```

### Added

- `docs/ESTRATEGIA_OPERACIONAL.md`;
- `docs/SPRINT_DOCS_ESTRATEGIA_OPERACIONAL.md`.

### Changed

- `docs/ARQUITETURA_V4.md` reconciliado com o estado real pós-Sprint 1.1-R;
- `engine/` registrado como fundação oficial do novo Decision Engine;
- `motor_ia/` registrado como legado isolado;
- estratégia operacional tornada leitura obrigatória para evolução do Decision Engine.

### Docs

Formalizados:

- venda sistemática de PUT;
- geração de renda recorrente;
- aquisição por exercício;
- foco em ativos de qualidade;
- horizonte de longo prazo;
- exercício não tratado como falha automática;
- qualidade e segurança antes de prêmio;
- preço líquido de aquisição;
- análise de rolagem;
- postura crítica da IA;
- governança de backlog.

### Validated

- 7 testes aprovados;
- nenhuma alteração funcional;
- diff restrito a `docs/`.

---

## 2026-07-10 — Encerramento da Sprint 1.1-R

Status: `Integrado`

Issue: `#1`

Pull Request: `#2`

Commit de merge:

```text
6e3416402e83a281dad4ab4a399ae3d4c059235b
```

### Added — Decision Engine

Fundação oficial do novo Decision Engine:

- `engine/__init__.py`;
- `engine/errors.py`;
- `engine/telemetry.py`;
- `engine/version.py`;
- `engine/core/__init__.py`;
- `engine/core/context.py`;
- `engine/core/pipeline.py`;
- `engine/providers/__init__.py`;
- `engine/providers/base.py`.

### Added — Testes

- `tests/test_engine_architecture.py`;
- `tests/test_engine_context.py`;
- `tests/test_engine_dependencies.py`;
- `tests/test_engine_errors.py`;
- `tests/test_engine_provider_contract.py`;
- `tests/test_engine_telemetry.py`.

### Added — Documentação

- `docs/SPRINT_01_R.md`;
- `docs/SPRINT_01_R_ENCERRAMENTO.md`.

### Added — Infraestrutura

- hierarquia estruturada de erros;
- telemetria local em memória;
- versão centralizada do motor;
- contexto de execução;
- pipeline pass-through;
- contrato abstrato de provider.

### Validated

Comando:

```bash
python -m unittest discover -s tests -v
```

Resultado:

```text
Ran 7 tests
OK
```

### Preserved

Permaneceram inalterados:

- Flask;
- `app.py`;
- rotas;
- templates;
- interface;
- banco;
- CSV;
- persistência;
- `motor_ia/`;
- funcionalidades existentes.

### Architecture

O novo `engine/` passou a representar a fundação oficial do futuro Decision Engine.

---

## 2026-07-09 — Abertura da Sprint 1.1-R

Status: `Concluído posteriormente`

### Contexto

Foi identificada divergência entre a documentação da Sprint 1.1 e o código real disponível na `main`.

### Decisão

Criar uma Sprint corretiva exclusiva para reconciliar a infraestrutura do Decision Engine sem implementar funcionalidades futuras.

### Escopo protegido

Ficaram explicitamente fora de escopo:

- indicadores;
- Score;
- ranking;
- scanner;
- integração Flask;
- providers reais;
- Machine Learning;
- refatoração do legado `motor_ia/`.

---

## Estado oficial atual do produto

Versão oficial do produto:

```text
FaculdadeMaria v4.3 - Score IA Inteligente
```

Versão interna atual do Decision Engine:

```text
1.1.0
```

O produto permanece funcionalmente baseado no monólito Flask existente, com:

- fundação independente do novo Decision Engine integrada;
- estratégia operacional oficial;
- Product Vision;
- backlog priorizado;
- regras permanentes;
- documentação de arquitetura e desenvolvimento.

---

## Próximas mudanças esperadas

Dependem de Sprints específicas e autorização do Product Owner.

Caminho crítico vigente:

1. contratos completos de oportunidade;
2. métricas operacionais de PUT;
3. normalização de dados;
4. indicadores técnicos puros;
5. qualidade do ativo;
6. filtros de segurança;
7. avaliador de PUT;
8. Score IA explicável;
9. ranking ajustado ao perfil;
10. serviço de Radar;
11. Radar Premium v1.

A ordem oficial de execução é confirmada pelo `BACKLOG.md`, pela especificação vigente e pela Sprint autorizada.
