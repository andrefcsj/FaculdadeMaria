# Sprint — Modal de Fechamento em Operações Abertas

**Projeto:** FaculdadeMaria  
**Status:** Concluída — aguardando aprovação para merge  
**Data:** 11/07/2026  
**Branch:** `agent/modal-fechamento-operacoes`

## Objetivo

Permitir o encerramento de uma operação diretamente na página Operações Abertas, sem navegar para uma página intermediária.

## Entregas

- modal Premium sobre a tabela de operações;
- abertura pelo botão de cadeado;
- opções Recompra, Exercida, Cancelar e Virou pó;
- data de encerramento;
- valor de recompra por opção;
- cálculo imediato do resultado final;
- validação de vencimento para Virou pó;
- confirmação assíncrona;
- retorno à própria página de Operações Abertas;
- persistência corrigida para CSV e PostgreSQL;
- resultado realizado registrado no campo existente;
- funcionamento por teclado e em dispositivos móveis;
- testes do cálculo e da rota.

## Regras financeiras preservadas

- exercício não é tratado como falha;
- nenhum preço de recompra é inventado;
- recompra usa o valor informado pelo usuário;
- Virou pó só é permitido no vencimento ou depois;
- nenhuma ordem é enviada à corretora.

## Compatibilidade

- a rota histórica `/fechar/<id>` permanece disponível;
- a página antiga de fechamento permanece como fallback sem JavaScript;
- schemas de CSV e PostgreSQL não foram alterados;
- Radar, Dashboard, Rolagem e Decision Engine permanecem intactos.

## Validação

- suíte automatizada completa;
- testes dos quatro métodos de encerramento;
- teste da persistência CSV;
- teste do retorno para Operações Abertas;
- verificação de sintaxe e renderização.

## Merge

Nenhum merge foi realizado. Aguardando autorização do Product Owner.
