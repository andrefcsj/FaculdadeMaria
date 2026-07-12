# Backlog Oficial — FaculdadeMaria

## 1. Status

Este documento é o backlog oficial do projeto FaculdadeMaria.

Toda nova ideia relevante para:

- seleção de oportunidades;
- análise de risco;
- rolagem;
- explicabilidade da IA;
- eficiência do capital;
- qualidade das recomendações;
- experiência Premium;
- robustez operacional;
- manutenção;
- escalabilidade;

deve ser registrada aqui antes de implementação, salvo correções críticas de segurança ou integridade tratadas por fluxo emergencial autorizado pelo Product Owner.

Nenhum item deste backlog autoriza implementação automática.

Cada item depende de Sprint específica, branch própria, testes, documentação e aprovação do Product Owner.

---

## 2. Convenções

### Prioridade

- `P0`: bloqueador, integridade, segurança ou requisito indispensável para próxima etapa.
- `P1`: alta prioridade e forte impacto no produto.
- `P2`: importante, mas pode aguardar etapas anteriores.
- `P3`: melhoria futura ou otimização.

### Status

- `DONE`: concluído e integrado oficialmente.
- `READY`: suficientemente definido para futura Sprint.
- `DISCOVERY`: precisa de validação técnica ou de produto.
- `BLOCKED`: depende de outro item.
- `FUTURE`: evolução posterior.

### Tipo

- `ARCH`: arquitetura.
- `ENGINE`: Decision Engine.
- `DATA`: dados de mercado.
- `RISK`: risco.
- `PUT`: estratégia de venda de PUT.
- `ROLL`: rolagem.
- `EXPLAIN`: explicabilidade.
- `UI`: experiência visual.
- `OPS`: operação e infraestrutura.
- `DOCS`: documentação e governança.
- `LEARN`: aprendizado futuro.

---

## 3. Estado atual consolidado

### Concluído

#### FM-DOC-001 — Fundação arquitetural documentada

- Prioridade: `P0`
- Tipo: `DOCS`
- Status: `DONE`

Entregas:

- arquitetura oficial;
- especificação do Decision Engine;
- roadmap;
- relatórios de Sprint;
- estratégia operacional oficial.

#### FM-ENG-001 — Fundação independente do Decision Engine

- Prioridade: `P0`
- Tipo: `ENGINE`
- Status: `DONE`

Entregas:

- pacote `engine/`;
- erros estruturados;
- telemetria;
- versão centralizada;
- contexto;
- pipeline pass-through;
- contrato abstrato de provider;
- testes de isolamento.

#### FM-GOV-001 — Estratégia operacional oficial

- Prioridade: `P0`
- Tipo: `DOCS`
- Status: `DONE`

Princípios formalizados:

- venda sistemática de PUT;
- exercício não tratado como falha automática;
- qualidade e segurança antes de prêmio;
- preço líquido de aquisição como critério central;
- análise de rolagem;
- explicabilidade;
- postura crítica da IA.

---

## 4. Caminho crítico até o primeiro Radar Premium

Esta seção define a sequência preferencial para chegar ao primeiro resultado visual útil sem sacrificar a qualidade do motor.

### FM-ENG-010 — Contrato completo de oportunidade

- Prioridade: `P0`
- Tipo: `ENGINE`
- Status: `DONE`
- Dependências: `FM-ENG-001`

Objetivo:

Definir contratos estáveis de entrada e saída para uma oportunidade de opção.

Campos mínimos esperados:

- ativo;
- código da opção;
- tipo da opção;
- vencimento;
- cotação atual;
- strike;
- prêmio;
- bid;
- ask;
- volume;
- negócios;
- liquidez;
- volatilidade implícita, quando disponível;
- timestamp;
- fonte;
- confiança do dado.

Critérios de aceite:

- contratos independentes de Flask;
- validação de dados;
- campos ausentes explicitamente tratados;
- testes determinísticos;
- compatibilidade futura com providers reais.

### FM-PUT-010 — Métricas operacionais de PUT

- Prioridade: `P0`
- Tipo: `PUT`
- Status: `DONE`
- Dependências: `FM-ENG-010`

Objetivo:

Criar métricas puras e auditáveis para venda de PUT.

Métricas:

- preço líquido de aquisição;
- desconto sobre mercado;
- ROI bruto;
- ROI líquido;
- ROI anualizado;
- distância percentual do strike;
- dias até vencimento;
- retorno por dia;
- capital nominal comprometido;
- eficiência do capital;
- retorno sobre margem, quando margem real estiver disponível.

Regras:

- premissas explícitas;
- custos nunca inventados;
- margem nunca estimada como fato;
- mesma entrada gera mesma saída.

### FM-DATA-010 — Snapshot normalizado de mercado

- Prioridade: `P0`
- Tipo: `DATA`
- Status: `DONE`
- Dependências: `FM-ENG-010`

Objetivo:

Normalizar dados de mercado independentemente do provider.

Capacidades:

- validar timestamp;
- identificar fonte;
- sinalizar dados ausentes;
- normalizar números;
- distinguir dado ausente de liquidez baixa;
- preservar rastreabilidade.

### FM-ENG-020 — Indicadores técnicos puros

- Prioridade: `P1`
- Tipo: `ENGINE`
- Status: `DONE`
- Dependências: `FM-DATA-010`

Indicadores iniciais:

- MM21;
- MM200;
- IFR14;
- Bandas de Bollinger;
- ATR;
- volatilidade histórica.

Critérios:

- funções puras;
- fixtures determinísticas;
- tratamento de histórico insuficiente;
- sem dependência de Flask;
- sem acesso direto a banco ou rede.

### FM-ASSET-010 — Qualidade do ativo

- Prioridade: `P0`
- Tipo: `RISK`
- Status: `DONE`
- Dependências: `FM-ENG-010`

Objetivo:

Evitar que prêmio alto faça o motor priorizar ativos inadequados para exercício e longo prazo.

Dimensões candidatas:

- elegibilidade manual inicial;
- liquidez do ativo base;
- histórico de negociação;
- tendência estrutural;
- volatilidade;
- concentração de carteira;
- deterioração de preço;
- eventos relevantes;
- adequação ao horizonte de longo prazo.

Decisão necessária:

Definir quais critérios podem ser objetivos com dados disponíveis e quais devem permanecer configuráveis pelo Product Owner.

### FM-RISK-010 — Filtros mínimos de segurança

- Prioridade: `P0`
- Tipo: `RISK`
- Status: `DONE`
- Dependências: `FM-PUT-010`, `FM-DATA-010`, `FM-ASSET-010`

Filtros candidatos:

- opção sem liquidez;
- spread excessivo;
- ROI abaixo do mínimo;
- vencimento fora da faixa;
- strike incompatível;
- dado ausente crítico;
- ativo inelegível;
- concentração excessiva;
- risco extremo;
- preço não confiável.

Requisito obrigatório:

Todo descarte deve possuir motivo explicável.

### FM-PUT-020 — Avaliador de venda de PUT

- Prioridade: `P0`
- Tipo: `PUT`
- Status: `DONE`
- Dependências: `FM-PUT-010`, `FM-RISK-010`, `FM-ENG-020`

Objetivo:

Avaliar uma oportunidade de PUT segundo a estratégia operacional oficial.

Saída esperada:

- elegibilidade;
- preço líquido;
- risco;
- retorno;
- segurança;
- fatores positivos;
- pontos de atenção;
- confiança.

### FM-SCORE-010 — Score IA inicial explicável

- Prioridade: `P0`
- Tipo: `ENGINE`
- Status: `DONE`
- Dependências: `FM-PUT-020`

Objetivo:

Gerar Score IA de 0 a 100 sem caixa-preta.

Requisitos:

- componentes auditáveis;
- pesos configuráveis;
- penalidades explícitas;
- confiança separada do score;
- rastreabilidade;
- testes;
- nenhum fator oculto.

Observação:

A ordem antiga de ranking deve ser revista para aderir à estratégia oficial, garantindo precedência real de qualidade do ativo, segurança e preço líquido sobre prêmio.

### FM-RANK-010 — Ranking ajustado ao perfil operacional

- Prioridade: `P1`
- Tipo: `ENGINE`
- Status: `DONE`
- Dependências: `FM-SCORE-010`

Critérios candidatos:

- elegibilidade;
- qualidade do ativo;
- segurança;
- Score IA;
- preço líquido;
- liquidez;
- risco;
- eficiência do capital;
- ROI ajustado;
- confiança dos dados.

### FM-EXPLAIN-010 — Explicação técnica inicial

- Prioridade: `P0`
- Tipo: `EXPLAIN`
- Status: `DONE`
- Dependências: `FM-SCORE-010`

Toda oportunidade deve apresentar:

- resumo;
- principais fatores positivos;
- principais fatores negativos;
- principal risco;
- impacto de dados ausentes;
- motivo da nota;
- conclusão técnica.

### FM-SVC-010 — Serviço de Radar

- Prioridade: `P0`
- Tipo: `ARCH`
- Status: `DONE`
- Dependências: `FM-RANK-010`, `FM-EXPLAIN-010`

Objetivo:

Criar a camada de serviço entre Flask e Decision Engine.

Regras:

- Flask não calcula score;
- Flask não calcula indicador;
- Flask não acessa provider do motor diretamente;
- serviço traduz contratos sem duplicar regra analítica.

### FM-UI-010 — Radar Premium v1

- Prioridade: `P0`
- Tipo: `UI`
- Status: `DONE`
- Dependências: `FM-SVC-010`

Objetivo:

Entregar o primeiro grande resultado visual do novo Decision Engine.

Componentes previstos:

- cabeçalho executivo;
- cards de resumo;
- tabela ou lista de oportunidades;
- Score IA;
- nota 0 a 10;
- badges de risco e liquidez;
- preço líquido;
- ROI bruto, líquido e anualizado;
- distância do strike;
- vencimento;
- pontos positivos;
- pontos de atenção;
- conclusão técnica;
- filtros;
- ordenação;
- estado vazio;
- carregamento;
- erro amigável;
- responsividade.

Direção visual:

- Premium;
- limpa;
- sofisticada;
- alta densidade informacional com boa hierarquia;
- sem excesso de cores;
- risco nunca escondido por estética.

---

## 5. Backlog de dados de mercado

### FM-DATA-020 — Provider real primário

- Prioridade: `P1`
- Tipo: `DATA`
- Status: `DONE`
- Dependências: `FM-DATA-010`

Objetivo:

Integrar uma fonte real de mercado por contrato substituível.

Requisitos:

- timeout;
- erro estruturado;
- timestamp;
- rate limit considerado;
- testes com mock;
- nenhuma dependência direta do Flask.

### FM-DATA-030 — Fallback entre providers

- Prioridade: `P2`
- Tipo: `DATA`
- Status: `BLOCKED`
- Dependências: `FM-DATA-020`

Objetivo:

Reduzir indisponibilidade por falha externa.

### FM-DATA-040 — Qualidade e confiança do dado

- Prioridade: `P1`
- Tipo: `DATA`
- Status: `DONE`
- Dependências: `FM-DATA-010`

Saída:

- completude;
- frescor;
- consistência;
- fonte;
- confiança.

---

## 6. Backlog de risco e eficiência do capital

### FM-RISK-020 — Spread bid/ask como risco operacional

- Prioridade: `P1`
- Tipo: `RISK`
- Status: `DONE`

Objetivo:

Evitar classificar como boa uma opção com prêmio teórico interessante e execução ruim.

### FM-RISK-030 — Distância do strike ajustada por ATR

- Prioridade: `P1`
- Tipo: `RISK`
- Status: `BLOCKED`
- Dependências: `FM-ENG-020`

### FM-RISK-040 — Concentração por ativo

- Prioridade: `P1`
- Tipo: `RISK`
- Status: `DISCOVERY`

Objetivo:

Penalizar novas operações que aumentem concentração excessiva.

### FM-RISK-050 — Concentração por vencimento

- Prioridade: `P2`
- Tipo: `RISK`
- Status: `DISCOVERY`

### FM-CAP-010 — Eficiência de capital

- Prioridade: `P0`
- Tipo: `RISK`
- Status: `DONE`
- Dependências: `FM-PUT-010`

Objetivo:

Comparar retorno com capital efetivamente comprometido.

### FM-CAP-020 — Retorno sobre margem real

- Prioridade: `P1`
- Tipo: `RISK`
- Status: `DISCOVERY`

Regra:

Só usar quando houver margem real ou premissa explicitamente identificada.

### FM-CAP-030 — Custo de oportunidade do capital

- Prioridade: `P2`
- Tipo: `RISK`
- Status: `FUTURE`

---

## 7. Backlog de rolagem

### FM-ROLL-010 — Detector de PUT aberta

- Prioridade: `P1`
- Tipo: `ROLL`
- Status: `DONE`

### FM-ROLL-020 — Lucro capturado e prêmio restante

- Prioridade: `P1`
- Tipo: `ROLL`
- Status: `DONE`
- Dependências: `FM-ROLL-010`

### FM-ROLL-030 — Comparador de rolagem

- Prioridade: `P1`
- Tipo: `ROLL`
- Status: `DONE`
- Dependências: `FM-ROLL-020`, `FM-RANK-010`

Comparar:

- operação atual;
- custo de recompra;
- nova venda;
- crédito ou débito líquido;
- strike;
- vencimento;
- preço líquido;
- risco;
- margem;
- retorno esperado.

### FM-ROLL-040 — Recomendação manter, fechar ou rolar

- Prioridade: `P1`
- Tipo: `ROLL`
- Status: `DONE`
- Dependências: `FM-ROLL-030`, `FM-EXPLAIN-010`

Regra obrigatória:

Nunca recomendar rolagem apenas para adiar prejuízo ou ocultar deterioração.

---

## 8. Backlog de explicabilidade

### FM-EXPLAIN-020 — Decomposição visual do Score IA

- Prioridade: `P1`
- Tipo: `EXPLAIN`
- Status: `BLOCKED`
- Dependências: `FM-SCORE-010`, `FM-UI-010`

### FM-EXPLAIN-030 — Comparação lado a lado

- Prioridade: `P1`
- Tipo: `EXPLAIN`
- Status: `BLOCKED`
- Dependências: `FM-RANK-010`

Objetivo:

Mostrar por que uma operação é melhor que outra.

### FM-EXPLAIN-040 — Confiança separada de qualidade

- Prioridade: `P0`
- Tipo: `EXPLAIN`
- Status: `DISCOVERY`

Objetivo:

Evitar confundir oportunidade boa com análise baseada em dado incompleto.

---

## 9. Backlog de experiência Premium

### FM-UI-020 — Design system mínimo

- Prioridade: `P1`
- Tipo: `UI`
- Status: `DONE`

Componentes:

- cores semânticas;
- tipografia;
- espaçamento;
- cards;
- tabelas;
- badges;
- botões;
- estados vazios;
- alertas;
- modais.

### FM-UI-030 — Comparador visual de oportunidades

- Prioridade: `P1`
- Tipo: `UI`
- Status: `BLOCKED`
- Dependências: `FM-UI-010`, `FM-EXPLAIN-030`

### FM-UI-040 — Painel executivo do Decision Engine

- Prioridade: `P2`
- Tipo: `UI`
- Status: `DONE`

Concluído e integrado pelo PR #48 em 11/07/2026, sem alteração das regras do Decision Engine.

### FM-UI-070 — Scanner Inteligente exploratório

- Prioridade: `P1`
- Tipo: `UI`
- Status: `DONE`
- Dependências: `FM-SVC-010`, providers de mercado disponíveis

Objetivo:

Separar a exploração completa do universo carregado do ranking curado apresentado pelo Radar de Oportunidades.

### FM-UI-080 — Operações Fechadas Executivas

- Prioridade: `P0`
- Tipo: `UI`
- Status: `DONE`

Entregas:

- histórico executivo filtrável;
- resultado e ROI realizados;
- edição, exclusão e reabertura seguras;
- metadados rastreáveis do encerramento.

### FM-UI-050 — Visão de risco da carteira

- Prioridade: `P2`
- Tipo: `UI`
- Status: `FUTURE`

### FM-UI-060 — Central de rolagem

- Prioridade: `P1`
- Tipo: `UI`
- Status: `DONE`
- Dependências: `FM-ROLL-040`

---

## 10. Backlog de gestão e arquitetura

### FM-ARCH-010 — Camada de serviços do Radar

- Prioridade: `P0`
- Tipo: `ARCH`
- Status: `DONE`
- Dependências: `FM-SVC-010`

### FM-ARCH-020 — Contratos de repositório

- Prioridade: `P2`
- Tipo: `ARCH`
- Status: `DISCOVERY`

### FM-ARCH-030 — Redução gradual de responsabilidades de `app.py`

- Prioridade: `P2`
- Tipo: `ARCH`
- Status: `FUTURE`

### FM-ARCH-040 — Observabilidade estruturada

- Prioridade: `P2`
- Tipo: `OPS`
- Status: `FUTURE`

### FM-ARCH-050 — CI automatizada

- Prioridade: `P1`
- Tipo: `OPS`
- Status: `DISCOVERY`

Objetivo:

Executar testes automaticamente em PRs.

---

## 11. Backlog operacional imediato

### FM-OPS-010 — Importação de notas de corretagem

- Prioridade: `P0`
- Tipo: `OPS`
- Status: `DONE`
- Dependências: contratos de operação e persistência existentes

Objetivo:

Permitir o envio de notas de corretagem para reduzir digitação manual e registrar operações com rastreabilidade.

Escopo inicial proposto:

- upload de PDF original;
- armazenamento seguro ou descarte explícito após processamento;
- extração de data, ativo, opção, compra/venda, quantidade, preço, custos e IRRF;
- tela de conferência obrigatória antes de salvar;
- prevenção de duplicidade;
- indicação de campos não reconhecidos;
- compatibilidade inicial com notas BTG/Necton;
- nenhuma operação criada silenciosamente.

Critérios obrigatórios:

- valores extraídos nunca tratados como corretos sem confirmação do usuário;
- documento não enviado a terceiros sem autorização explícita;
- testes com documentos anonimizados;
- falha de leitura não pode alterar a carteira;
- trilha de origem da informação preservada.

---

## 12. Backlog de aprendizado futuro

### FM-LEARN-010 — Histórico de decisões

- Prioridade: `P2`
- Tipo: `LEARN`
- Status: `FUTURE`

### FM-LEARN-020 — Comparação expectativa x resultado

- Prioridade: `P2`
- Tipo: `LEARN`
- Status: `BLOCKED`
- Dependências: `FM-LEARN-010`

### FM-LEARN-030 — Métricas de acerto por critério

- Prioridade: `P3`
- Tipo: `LEARN`
- Status: `FUTURE`

### FM-LEARN-040 — Ajuste assistido de pesos

- Prioridade: `P3`
- Tipo: `LEARN`
- Status: `FUTURE`

Regra:

Nenhum peso pode ser alterado automaticamente sem auditoria e governança.

### FM-LEARN-050 — Machine Learning

- Prioridade: `P3`
- Tipo: `LEARN`
- Status: `FUTURE`

Condição:

Somente após base histórica suficiente, critérios validados e aprovação explícita.

---

## 13. Ideias registradas automaticamente pela política operacional

### FM-IDEA-001 — Qualidade do ativo antes do prêmio

- Prioridade: `P0`
- Status: `READY`

Origem:

Perfil operacional oficial do Product Owner.

### FM-IDEA-002 — Preço líquido como eixo central

- Prioridade: `P0`
- Status: `READY`

### FM-IDEA-003 — Rolagem automática quando houver PUT aberta

- Prioridade: `P1`
- Status: `READY`

### FM-IDEA-004 — Alternativa melhor obrigatória

- Prioridade: `P1`
- Status: `DISCOVERY`

Objetivo:

Quando o motor identificar operação claramente superior, mostrar a alternativa em vez de apenas avaliar a sugestão original.

### FM-IDEA-005 — Penalização de ROI alto causado por risco extremo

- Prioridade: `P1`
- Status: `DISCOVERY`

### FM-IDEA-006 — Confiança de dados separada do Score IA

- Prioridade: `P0`
- Status: `DISCOVERY`

### FM-IDEA-007 — Exercício bem-sucedido por preço líquido

- Prioridade: `P0`
- Status: `DISCOVERY`

Objetivo:

Avaliar resultado do exercício pelo preço líquido e qualidade do ativo, não por regra binária de sucesso ou falha.

### FM-IDEA-008 — Score de eficiência do capital

- Prioridade: `P1`
- Status: `DISCOVERY`

### FM-IDEA-009 — Comparador de mesma PUT em strikes diferentes

- Prioridade: `P1`
- Status: `DISCOVERY`

### FM-IDEA-010 — Comparador entre ativos

- Prioridade: `P1`
- Status: `DISCOVERY`

### FM-IDEA-011 — Explicação de por que não operar

- Prioridade: `P1`
- Status: `DISCOVERY`

Objetivo:

O motor deve ser capaz de concluir que nenhuma oportunidade atual é suficientemente boa.

### FM-IDEA-012 — Modo diagnóstico de descartados

- Prioridade: `P2`
- Status: `DISCOVERY`

### FM-IDEA-013 — Alertas de concentração antes da entrada

- Prioridade: `P1`
- Status: `DISCOVERY`

### FM-IDEA-014 — Radar com foco em qualidade, não em quantidade

- Prioridade: `P0`
- Status: `READY`

### FM-IDEA-015 — Trilha visual da decisão

- Prioridade: `P1`
- Status: `DISCOVERY`

Objetivo:

Mostrar visualmente como qualidade, risco, liquidez, preço líquido e retorno contribuíram para a conclusão.

---

## 14. Sequência recomendada de próximas Sprints

1. `FM-ARCH-050` — executar testes automaticamente em Pull Requests;
2. `FM-EXPLAIN-040` — separar visualmente confiança do dado e qualidade da oportunidade;
3. `FM-RISK-040` — controlar concentração por ativo;
4. `FM-UI-030` — comparar oportunidades lado a lado.

As Sprints Funcionais A–J, o Radar, o Scanner e o Dashboard Executivo já foram integrados e não constituem trabalho futuro.

---

## 15. Regra de atualização do backlog

Ao surgir nova ideia:

1. registrar um identificador único;
2. descrever problema e objetivo;
3. indicar prioridade inicial;
4. indicar dependências;
5. não implementar automaticamente;
6. revisar na próxima Sprint apropriada;
7. registrar mudança de status no changelog quando relevante.

O backlog deve permanecer vivo, mas nunca pode substituir o escopo formal de uma Sprint.
