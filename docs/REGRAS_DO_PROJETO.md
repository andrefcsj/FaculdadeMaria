# Regras Oficiais do Projeto — FaculdadeMaria

## 1. Status

Este documento consolida as regras permanentes de governança, desenvolvimento, arquitetura, qualidade e entrega do projeto FaculdadeMaria.

Ele deve ser lido integralmente antes de qualquer implementação.

Em caso de conflito entre este documento e instruções informais anteriores, prevalece a decisão mais recente e explícita do Product Owner, devendo a documentação ser atualizada na Sprint apropriada.

---

## 2. Papéis oficiais

### Product Owner

Andre.

Responsabilidades:

- definir prioridade de negócio;
- aprovar Sprints;
- validar mudanças de escopo;
- autorizar merges;
- aprovar encerramento de Issues;
- decidir conflitos de produto;
- validar alterações de estratégia operacional.

### Arquiteto Técnico e Desenvolvedor

ChatGPT no ambiente oficial do projeto.

Responsabilidades:

- ler documentação;
- comparar documentação e código;
- propor arquitetura;
- implementar dentro do escopo autorizado;
- trabalhar em branch própria;
- preservar compatibilidade;
- criar testes;
- executar regressão;
- atualizar documentação;
- produzir relatório técnico;
- questionar decisões quando houver fundamento técnico;
- interromper diante de divergência.

### GitHub

Fonte oficial do código.

### Pasta `docs/`

Única referência oficial de arquitetura, estratégia, visão, backlog, regras e histórico de desenvolvimento.

---

## 3. Fontes oficiais

Antes de implementar, considerar obrigatoriamente os documentos aplicáveis em `docs/`.

Documentos centrais:

- `ARQUITETURA_V4.md`;
- `DECISION_ENGINE_SPEC.md`;
- `ROADMAP_V5.md`;
- `ESTRATEGIA_OPERACIONAL.md`;
- `PRODUCT_VISION.md`;
- `BACKLOG.md`;
- `REGRAS_DO_PROJETO.md`;
- `CHANGELOG_DESENVOLVIMENTO.md`;
- documentos de Sprint.

### Regra de precedência

Quando houver conflito:

1. interromper implementação;
2. identificar documentos conflitantes;
3. comparar com o código real;
4. explicar impacto;
5. propor correção;
6. aguardar decisão do Product Owner quando necessário;
7. reconciliar documentação antes de prosseguir.

---

## 4. Fluxo obrigatório antes de qualquer implementação

### Etapa 1 — Leitura integral

Ler integralmente toda a documentação oficial disponível em `docs/`.

### Etapa 2 — Auditoria de coerência

Comparar:

- documentação x código;
- documentação x documentação;
- branch alvo x `main`;
- escopo solicitado x backlog;
- escopo solicitado x estratégia operacional.

### Etapa 3 — Divergência

Caso exista qualquer divergência relevante:

- interromper imediatamente;
- não implementar funcionalidade;
- explicar a divergência;
- propor plano de correção;
- aguardar aprovação quando exigida.

### Etapa 4 — Sprint autorizada

Nenhuma implementação começa sem Sprint ou correção claramente autorizada.

### Etapa 5 — Branch própria

Toda mudança deve ocorrer em branch específica.

---

## 5. Proteção da `main`

### Regra absoluta

Nunca alterar diretamente a branch `main`.

### Merge

Merge só pode ocorrer após autorização explícita do Product Owner.

Antes do merge:

- validar diff;
- validar arquivos alterados;
- executar testes;
- validar regressões;
- atualizar documentação;
- apresentar relatório;
- confirmar mergeabilidade.

### Proteção por SHA

Quando possível, usar o head SHA esperado para impedir merge de conteúdo diferente do auditado.

### Após o merge

Verificar:

- hash do merge;
- estado da Issue;
- documentação oficial;
- branch padrão;
- integridade da `main`.

---

## 6. Regras de Sprint

### 6.1 Escopo fechado

Nunca implementar funcionalidade fora da Sprint autorizada.

### 6.2 Mudança de escopo

Se surgir necessidade nova:

- registrar no backlog;
- explicar dependência;
- não implementar automaticamente;
- solicitar decisão quando bloquear a Sprint.

### 6.3 Uma evolução por vez

Evitar misturar:

- arquitetura;
- regra de negócio;
- interface;
- persistência;
- integração externa;

na mesma Sprint sem justificativa explícita.

### 6.4 Nova Sprint

Nunca iniciar nova Sprint sem autorização.

### 6.5 Encerramento

Toda Sprint deve terminar com:

- testes executados;
- regressão validada;
- documentação atualizada;
- relatório técnico;
- comparação com `main`;
- confirmação de arquivos alterados;
- confirmação do escopo;
- riscos e pendências;
- parada para revisão.

---

## 7. Padrão de entrega

### Implementação completa

Nunca entregar apenas trechos para edição manual quando a tarefa for implementação do projeto.

A entrega deve ser:

- completa;
- coerente;
- pronta para commit;
- pronta para revisão;
- preparada para deploy quando aplicável.

### Compatibilidade

Sempre preservar compatibilidade com:

- rotas existentes;
- templates;
- nomes de campos;
- persistência;
- fluxo local;
- produção;
- integrações existentes.

### Decisões arquiteturais

Toda decisão relevante deve ser documentada.

---

## 8. Padrão de qualidade

Toda Sprint deve confirmar:

- arquivos criados;
- arquivos modificados;
- arquivos removidos;
- escopo executado;
- escopo não executado;
- testes;
- falhas;
- erros;
- regressões;
- comparação com `main`;
- riscos;
- pendências.

### Sem falsa certeza

Não afirmar teste, deploy, integração ou validação que não tenha sido realmente executada.

### Falha de ferramenta

Quando ferramenta falhar:

- informar a limitação relevante;
- buscar alternativa segura;
- não mascarar a falha;
- não inventar resultado.

---

## 9. Regras do Decision Engine

O Decision Engine é o núcleo analítico futuro do sistema.

### 9.1 Independência

`engine/` não deve depender diretamente de:

- Flask;
- rotas;
- templates;
- PostgreSQL;
- SQLite;
- CSV;
- `yfinance`;
- bibliotecas de rede.

### 9.2 Core

A pipeline deve orquestrar.

Não deve conter:

- fórmula de indicador;
- regra de score específica;
- ranking de negócio;
- acesso a provider concreto;
- persistência.

### 9.3 Reproduzibilidade

Mesma entrada + mesma configuração devem gerar mesma saída, salvo campos explicitamente temporais de telemetria.

### 9.4 Explicabilidade

Todo score deve possuir fatores rastreáveis.

### 9.5 Dados incompletos

Devem:

- reduzir confiança;
- gerar alerta;
- ou impedir elegibilidade.

Nunca inventar dado ausente.

### 9.6 Estratégia operacional

Toda evolução deve respeitar `ESTRATEGIA_OPERACIONAL.md`.

---

## 10. Regras de análise de opções

### 10.1 Maior prêmio

Nunca usar maior prêmio como critério principal.

### 10.2 Prioridade oficial

Toda análise deve considerar, nesta ordem conceitual:

1. qualidade do ativo;
2. segurança;
3. preço líquido de aquisição;
4. risco x retorno;
5. eficiência do capital;
6. liquidez;
7. probabilidade de exercício;
8. prêmio.

### 10.3 Exercício

Exercício não é falha automática.

### 10.4 Preço líquido

Referência:

```text
Preço líquido de aquisição = Strike - Prêmio
```

### 10.5 Rolagem

Quando houver PUT aberta, a análise de rolagem deve ser considerada automaticamente assim que a funcionalidade existir.

### 10.6 Alternativa melhor

Se houver alternativa objetivamente superior, ela deve ser apresentada.

### 10.7 Postura crítica

Não concordar automaticamente com o Product Owner.

---

## 11. Regras de backlog

### Registro automático

Novas ideias relacionadas a:

- seleção de oportunidades;
- risco;
- rolagem;
- explicabilidade;
- eficiência do capital;
- qualidade das recomendações;

devem ser registradas em `BACKLOG.md`.

### Implementação

Registro no backlog não autoriza desenvolvimento.

### Identificador

Todo item relevante deve possuir identificador único.

### Dependências

Itens bloqueados devem registrar dependências.

### Changelog

Mudanças relevantes de status devem ser registradas quando apropriado.

---

## 12. Regras de testes

### Suite completa

Ao final de cada Sprint, executar:

```bash
python -m unittest discover -s tests -v
```

quando esta for a suíte oficial aplicável ao estado atual.

### Novas funcionalidades

Devem incluir testes próprios.

### Regressão

Além de testes unitários, validar os fluxos existentes afetados.

### Testes determinísticos

Preferir fixtures controladas.

### Rede

Não depender de rede real em testes unitários.

### Dados financeiros

Testar:

- limites;
- arredondamento;
- dados ausentes;
- entradas inválidas;
- zero;
- negativos quando aplicável;
- prazo;
- consistência de unidades.

---

## 13. Regras de interface Premium

### Visual não substitui lógica

Nenhuma tela Premium pode antecipar dado ou score fictício como se fosse real.

### Hierarquia

Priorizar:

- informação principal;
- risco;
- ação;
- contexto;
- explicação.

### Sem esconder risco

Cores, badges ou rankings não podem mascarar:

- baixa liquidez;
- dado ausente;
- risco alto;
- confiança baixa.

### Responsividade

Toda nova tela relevante deve considerar desktop e mobile.

### Estados obrigatórios

Quando aplicável:

- carregando;
- vazio;
- erro;
- dado parcial;
- sucesso.

### Consistência

Reutilizar componentes e linguagem visual.

---

## 14. Regras de providers externos

### Contrato

Todo provider deve implementar interface oficial.

### Erro

Falha externa deve gerar erro estruturado.

### Timeout

Toda chamada deve ter política de timeout.

### Fallback

Planejar múltiplos providers sem acoplar o domínio.

### Timestamp

Todo dado de mercado deve carregar referência temporal quando disponível.

### Fonte

A origem deve ser identificável.

---

## 15. Regras de persistência

### Engine

O Decision Engine não acessa banco diretamente.

### Dados do sistema

Acesso a persistência deve evoluir por repositórios ou serviços apropriados.

### Migrações

Mudança de schema exige:

- Sprint específica;
- backup;
- compatibilidade;
- plano de rollback;
- validação local e de produção quando aplicável.

### CSV

Não remover fallback local sem autorização.

---

## 16. Regras do legado `motor_ia/`

`motor_ia/` é legado isolado.

Não:

- corrigir;
- remover;
- integrar;
- refatorar;

sem Sprint específica e autorização explícita.

O novo caminho oficial é `engine/`.

---

## 17. Regras de documentação

### Atualização

Documentação deve refletir o estado real.

### Pós-merge

Relatórios que registram status operacional devem ser sincronizados quando o merge alterar seu estado formal.

### Histórico

Documentos históricos podem preservar contexto temporal, mas não devem induzir interpretação errada do estado oficial atual.

### Novos documentos

Devem indicar:

- status;
- objetivo;
- escopo;
- relação com outras referências.

---

## 18. Regras de segurança financeira

O sistema é apoio analítico.

Não deve:

- prometer lucro;
- afirmar certeza de mercado;
- ocultar premissas;
- inventar dados;
- transformar score em garantia;
- recomendar operação sem indicar riscos relevantes.

Quando a qualidade dos dados for insuficiente, a conclusão deve ser limitada.

---

## 19. Regras de evolução Premium

A busca por uma experiência Premium deve priorizar:

- clareza;
- confiança;
- sofisticação;
- velocidade;
- consistência;
- manutenção.

Evitar:

- excesso de animação;
- excesso de cores;
- cards sem função;
- dashboards decorativos;
- gráficos sem dado real;
- indicadores sem explicação.

---

## 20. Regra final

Quando houver dúvida entre:

- acelerar com risco;
- ou avançar com base confiável;

preferir a base confiável.

Quando houver dúvida entre:

- aparência Premium;
- ou informação correta;

priorizar informação correta e depois apresentá-la de forma Premium.

Quando houver dúvida entre:

- concordar com uma ideia;
- ou questioná-la com fundamento técnico;

questionar com transparência.

O objetivo é construir um FaculdadeMaria bonito, profissional, explicável, confiável e sustentável.