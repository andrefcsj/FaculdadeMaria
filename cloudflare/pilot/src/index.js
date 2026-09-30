/**
 * Ambiente de homologação isolado para a migração ao Cloudflare.
 *
 * Este Worker não atende o domínio radarpulse.com.br, não acessa dados
 * operacionais e não substitui a aplicação Flask em produção.
 */
export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname !== "/health") {
      return new Response("FaculdadeMaria Cloudflare pilot", {
        headers: { "content-type": "text/plain; charset=utf-8" },
      });
    }

    const result = await env.DB.prepare("SELECT 1 AS ok").first();
    return Response.json({
      service: "faculdademaria-pilot",
      status: result?.ok === 1 ? "ok" : "degraded",
      environment: "isolated-test",
      productionChanged: false,
    });
  },
};
