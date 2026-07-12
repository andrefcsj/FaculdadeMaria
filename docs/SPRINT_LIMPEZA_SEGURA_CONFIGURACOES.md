# Sprint — Limpeza Segura em Configurações

**Status:** Concluída  
**Data:** 12/07/2026

## Entregas

- Configurações reformulada em padrão Premium;
- exclusão de operações abertas em um mês específico;
- exclusão de operações abertas em um ano específico;
- reset completo do ambiente operacional;
- prévia dos registros afetados;
- confirmação escrita obrigatória;
- senha administrativa externa ao código;
- link de backup antes da exclusão;
- remoção coordenada de operações, notas vinculadas, encerramentos e histórico legado;
- recálculo automático após exclusão;
- compatibilidade CSV e PostgreSQL.

## Preservado em qualquer limpeza

- configurações da estratégia;
- capital e ROI configurados;
- universo de ativos;
- dados e estrutura do Radar;
- código, documentação e sistema;
- backups previamente baixados.

## Segurança

- comandos destrutivos ficam bloqueados sem `ADMIN_RESET_PIN` no Render;
- comparação segura da senha;
- texto de confirmação varia por período;
- transação PostgreSQL com rollback em falha;
- reset não é executado automaticamente após o deploy.

## Uso para começar do zero

Depois do deploy e da configuração de `ADMIN_RESET_PIN`, acessar Configurações, baixar um backup, selecionar Zerar ambiente operacional, informar a senha e digitar `ZERAR FACULDADEMARIA`.

## Validação

- exclusão mensal seletiva testada;
- reset completo testado;
- preservação de configuração testada;
- senha e confirmação testadas;
- suíte automática executada antes do merge.
