# Sprint — Caixa da Corretora e DARFs Pagos

**Status:** Concluída  
**Data:** 12/07/2026

## Entregas

- menu Cadastrar Operação reposicionado acima de Operações Abertas;
- menu Novos Aportes;
- cadastro de aportes e retiradas;
- aportes líquidos incorporados ao capital total utilizado nos indicadores;
- livro-caixa evolutivo com saldo após cada lançamento;
- integração de notas, operações manuais, recompras e exercícios no caixa calculado;
- card Saldo na Corretora no Dashboard;
- menu e página DARFs Pagos;
- cadastro manual de DARF sem necessidade de documento de demonstração;
- PDF opcional com hash de duplicidade e descarte do original;
- filtros mensal, anual e histórico completo;
- gráfico de evolução dos DARFs pagos;
- exclusão de registros com confirmação;
- persistência PostgreSQL e JSON local;
- integração dos novos históricos com a limpeza segura.

## Definição do saldo

O saldo exibido é contábil e calculado pelo FaculdadeMaria:

`aportes + créditos de notas e operações - retiradas - compras - recompras - exercícios registrados`.

Sem integração bancária com o BTG, o valor não é apresentado como consulta ao vivo e deve ser conciliado periodicamente com a corretora.

## DARFs sem documento real

A primeira versão funciona por cadastro manual. O PDF é aceito apenas para identificação por hash; não há extração automática até que um documento real seja validado.

## Segurança

- nenhum PDF de DARF é armazenado;
- valores não são inferidos;
- saldo evita duplicar operações já vinculadas a notas;
- DARF pago não altera apuração fiscal nem operações;
- reset operacional inclui aportes, retiradas e DARFs.

## Validação

- aportes e retiradas testados;
- saldo recalculado testado;
- DARF manual e duplicidade testados;
- páginas, menus e ordem de navegação testados;
- suíte completa executada localmente e no GitHub Actions.
