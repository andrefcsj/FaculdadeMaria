# Sprint — Cadastrar Nova Operação em modal Premium

**Status:** concluída

## Entregas

- popup global com o título `Cadastrar Nova Operação`;
- Venda/Compra e CALL/PUT;
- máscaras monetárias BRL;
- identificação automática do ativo subjacente;
- preenchimento de strike, vencimento, prêmio e cotação quando o código existir no mercado importado ou em cadastro anterior;
- ausência de dados não gera valores inventados;
- salvamento assíncrono sem mudança de página;
- fechamento automático do popup após salvar;
- acesso pelo menu lateral;
- ajuste complementar de alinhamento da tabela de Operações Abertas.

## Compatibilidade

A rota histórica `/nova` foi preservada. O novo fluxo usa `/api/operacoes` e não altera o schema existente.