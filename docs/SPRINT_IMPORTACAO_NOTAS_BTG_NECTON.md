# Sprint — Importação de Notas BTG/Necton

**Status:** Concluída  
**Data:** 12/07/2026

## Entregas

- upload de nota PDF dentro do modal Cadastrar Operação;
- parser específico para o layout BTG Pactual/Necton;
- preenchimento de código, compra/venda, tipo, quantidade, prêmio, custos e IRRF;
- conferência obrigatória de strike e vencimento quando ausentes no documento;
- vínculo da nota somente depois do cadastro confirmado;
- prevenção de duplicidade por hash e índice da negociação;
- substituição de Importar Mercado por Notas Importadas no menu;
- central Premium de créditos, débitos e custos por mês e ano;
- gráfico vermelho restrito a custos, taxas e impostos;
- gráfico verde de créditos líquidos;
- compras de ativos e opções separadas do gráfico de custos;
- painel conservador de possível DARF;
- persistência estruturada em PostgreSQL no Render e JSON local;
- descarte do PDF original depois da leitura.

## Regra fiscal

Crédito recebido na abertura de uma venda de PUT não é apresentado como lucro tributável realizado. O sistema não gera DARF definitivo sem identificar fechamento, exercício ou expiração, custos, IRRF e prejuízos compensáveis.

## Segurança e privacidade

- PDF limitado a 5 MB;
- somente PDF BTG/Necton é aceito;
- documento original não é armazenado;
- dados extraídos precisam ser conferidos pelo usuário;
- falha de leitura não altera a carteira;
- nenhuma informação é enviada a terceiros.

## Validação

- nota real fornecida pelo Product Owner validada localmente;
- fixture anonimizada usada nos testes;
- custos efetivos de R$ 1,08 confirmados contra líquido de R$ 31,92;
- prevenção de duplicidade e exclusão de compras no gráfico testadas.
