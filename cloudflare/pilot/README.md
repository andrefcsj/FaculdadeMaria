# Ambiente-piloto Cloudflare

Este diretório contém exclusivamente a prova de conectividade da migração.

- Worker: `faculdademaria-pilot`;
- banco D1: `faculdademaria-pilot`;
- URL provisória: `https://faculdademaria-pilot.radarpulse.com.br`;
- subdomínio próprio, sem alterar `www.radarpulse.com.br` ou acessar dados de produção.

O endpoint `/health` confirma que o Worker e o D1 estão ativos. A aplicação Flask só será introduzida após a camada de persistência ter sido adaptada e testada.
