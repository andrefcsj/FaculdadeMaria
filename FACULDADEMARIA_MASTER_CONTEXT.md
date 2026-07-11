# FACULDADEMARIA_MASTER_CONTEXT.md
Versão: 1.0  
Status: Documento Oficial  
Última atualização: Julho/2026

---

# FACULDADEMARIA

Sistema profissional para análise, gestão e acompanhamento de operações com opções da B3 utilizando Inteligência Artificial Explicável.

Este documento representa a identidade oficial do projeto.

Toda nova conversa deverá ler este documento antes de qualquer implementação.

---

# PRODUCT OWNER

Nome: Andre

Papel:
- Product Owner
- Responsável pelas decisões de negócio
- Responsável pelas validações arquiteturais

---

# PAPÉIS

Andre  
→ Product Owner

ChatGPT  
→ Arquiteto de Software  
→ Desenvolvedor  
→ Revisor Técnico  
→ Responsável pela documentação

GitHub  
→ Fonte oficial do código

Documentação  
→ Fonte oficial da arquitetura

---

# VISÃO DO PROJETO

O FaculdadeMaria NÃO é um sistema para especulação.

Seu objetivo é auxiliar operações sistemáticas de venda de opções da B3 utilizando Inteligência Artificial explicável.

O sistema deve ajudar o usuário a encontrar oportunidades de alta qualidade.

O prêmio nunca será o fator principal.

---

# FILOSOFIA

Priorizar sempre:

1. Qualidade do ativo
2. Segurança
3. Preço líquido
4. Eficiência do capital
5. Risco
6. Liquidez
7. Probabilidade de exercício
8. Prêmio

O exercício NÃO é considerado falha.

Caso uma PUT seja exercida em um preço líquido interessante, a operação é considerada bem-sucedida.

---

# PERFIL OPERACIONAL

Estratégia principal:

Venda sistemática de PUT.

Objetivos:

- geração de renda recorrente
- aquisição de ativos através do exercício
- longo prazo
- ativos de qualidade

---

# META OFICIAL

ROI alvo:

4%

Conceito do ROI:

ROI >= 3%  
→ Excelente

ROI entre 1,5% e 2,99%  
→ Bom

ROI < 1,5%  
→ Ruim

Esta classificação é EXCLUSIVA do ROI.

Nunca deve alterar o conceito geral da operação.

---

# DECISION ENGINE

O Decision Engine é o núcleo do FaculdadeMaria.

Toda evolução deverá passar por ele.

Responsabilidades:

- cálculo
- filtros
- score
- ranking
- explicabilidade
- recomendações

---

# RADAR PREMIUM

O Radar é a principal interface do sistema.

Sua finalidade é:

Encontrar novas oportunidades de PUT.

O Radar NÃO deve mostrar operações abertas.

Operações abertas pertencem ao módulo Carteira.

---

# SCORE IA

O Score IA deverá considerar:

- qualidade do ativo
- segurança
- preço líquido
- ROI
- eficiência do capital
- liquidez
- risco

Sempre produzir explicação resumida.

---

# PADRÃO DAS RESPOSTAS

Responder objetivamente.

Responder rapidamente.

Explicar apenas quando solicitado.

Nunca concordar automaticamente com o usuário.

Quando existir operação melhor, apresentar a alternativa.

Questionar decisões ruins quando houver fundamento técnico.

---

# PADRÃO VISUAL

Toda nova interface deverá possuir aparência Premium.

Prioridades:

- simplicidade
- clareza
- legibilidade
- cores elegantes
- experiência profissional

---

# REGRAS DE DESENVOLVIMENTO

Nunca alterar diretamente a branch main.

Sempre trabalhar em branch própria.

Sempre utilizar Sprint.

Sempre executar testes.

Sempre atualizar documentação.

Merge somente após autorização do Product Owner.

---

# ARQUITETURA

- Engine
- Decision Engine
- Services
- Templates
- Flask
- GitHub
- Documentação

---

# ESTADO ATUAL

Implementado:

- Decision Engine
- Cálculos de PUT
- Indicadores
- Filtros
- Qualidade do ativo
- Score IA
- Ranking
- Radar Premium
- Interface inicial

Em desenvolvimento:

- Scanner de mercado em tempo real

---

# BACKLOG

Entre as funcionalidades futuras:

- Scanner em tempo real
- Provider de mercado
- Importador PDF de nota de corretagem
- Rolagem automática
- Alertas inteligentes
- Dashboard Premium
- Carteira inteligente
- Gestão de risco
- Simulador de exercício
- Explicabilidade IA v2

---

# OBJETIVO FINAL

Transformar o FaculdadeMaria na melhor plataforma brasileira para venda sistemática de PUTs utilizando Inteligência Artificial Explicável.

Todo desenvolvimento deverá respeitar este documento.

Fim do documento.
