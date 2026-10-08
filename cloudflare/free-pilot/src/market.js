import universe from "./asset-universe.json" with { type: "json" };
const output = (value, status = 200) =>
  new Response(JSON.stringify(value), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
    },
  });
const validSymbol = (s) => /^[A-Z0-9]{4,12}$/.test(s);
const numeric = (v) =>
  v === null || v === undefined || v === ""
    ? null
    : Number.isFinite(Number(v))
      ? Number(v)
      : null;
const date = () =>
  new Intl.DateTimeFormat("sv-SE", { timeZone: "America/Sao_Paulo" }).format(
    new Date(),
  );
async function upstream(url, token) {
  const response = await fetch(url, {
    headers: {
      Accept: "application/json",
      ...(token
        ? { Authorization: `Bearer ${token}` }
        : { "User-Agent": "FaculdadeMaria/1.0" }),
    },
    signal: AbortSignal.timeout(20000),
  });
  if (!response.ok)
    throw Error(`Fonte de mercado respondeu HTTP ${response.status}.`);
  const payload = await response.json();
  if (payload.success === false)
    throw Error("Fonte de mercado recusou a consulta.");
  return payload;
}
async function cache(env, kind, symbol, loader, ttl) {
  const stored = await env.DB.prepare(
    "SELECT payload, updated_at FROM market_snapshots WHERE snapshot_kind = ? AND symbol = ?",
  )
    .bind(kind, symbol)
    .first();
  if (stored && Date.now() - Date.parse(stored.updated_at) < ttl)
    return { ...JSON.parse(stored.payload), cached: true };
  try {
    const result = await loader();
    await env.DB.prepare(
      "INSERT INTO market_snapshots(snapshot_kind, symbol, payload, updated_at) VALUES(?, ?, ?, ?) ON CONFLICT(snapshot_kind, symbol) DO UPDATE SET payload = excluded.payload, updated_at = excluded.updated_at",
    )
      .bind(kind, symbol, JSON.stringify(result), new Date().toISOString())
      .run();
    return { ...result, cached: false };
  } catch (error) {
    if (stored)
      return {
        ...JSON.parse(stored.payload),
        cached: true,
        stale: true,
        warning: error.message,
      };
    throw error;
  }
}
export async function handleMarket(request, env, path) {
  const url = new URL(request.url);
  if (path === "/api/market/status")
    return output({
      sldx_configured: Boolean(env.SLDX_API_TOKEN),
      universe,
      sources: [
        "SLDX",
        "B3 COTAHIST",
        "CVM DFP",
        "CSV",
        "Yahoo Finance histórico",
      ],
    });
  if (path === "/api/market/profiles" && request.method === "GET") {
    const rows = await env.DB.prepare(
      "SELECT payload FROM market_snapshots WHERE snapshot_kind = 'quality'",
    ).all();
    return output({
      profiles: Object.fromEntries(
        universe
          .map((u) => [u.asset, u])
          .concat(
            rows.results.map((x) => {
              const p = JSON.parse(x.payload);
              return [p.asset, p];
            }),
          ),
      ),
    });
  }
  if (path === "/api/market/profiles" && request.method === "POST") {
    const body = await request.json();
    if (
      !Array.isArray(body.profiles) ||
      !body.profiles.length ||
      body.profiles.length > 100
    )
      return output({ error: "Informe até 100 perfis de qualidade." }, 400);
    const profiles = body.profiles;
    if (
      profiles.some(
        (p) =>
          !validSymbol(p.asset) ||
          ![p.quality_score, p.data_confidence].every(
            (v) =>
              v === null ||
              (numeric(v) !== null && numeric(v) >= 0 && numeric(v) <= 1),
          ) ||
          typeof p.assignment_eligible !== "boolean" ||
          typeof p.long_term_suitable !== "boolean",
      )
    )
      return output({ error: "Perfil de qualidade inválido." }, 400);
    await env.DB.batch(
      profiles.map((p) =>
        env.DB.prepare(
          "INSERT INTO market_snapshots(snapshot_kind,symbol,payload,updated_at) VALUES('quality',?,?,?) ON CONFLICT(snapshot_kind,symbol) DO UPDATE SET payload=excluded.payload,updated_at=excluded.updated_at",
        ).bind(p.asset, JSON.stringify(p), new Date().toISOString()),
      ),
    );
    return output({ ok: true, updated: profiles.length });
  }
  if (path === "/api/market/import" && request.method === "POST") {
    const body = await request.json();
    if (
      !Array.isArray(body.opportunities) ||
      !body.opportunities.length ||
      body.opportunities.length > 5000
    )
      return output({ error: "Informe de 1 a 5.000 opções válidas." }, 400);
    const groups = new Map();
    for (const o of body.opportunities) {
      if (
        !validSymbol(o.asset) ||
        !/^[A-Z0-9]{4,20}$/.test(o.option_code) ||
        !["PUT", "CALL"].includes(o.option_type) ||
        !(numeric(o.spot_price) > 0) ||
        !(numeric(o.strike) > 0) ||
        !(numeric(o.premium) >= 0) ||
        !/^\d{4}-\d{2}-\d{2}$/.test(o.expiry)
      )
        return output({ error: "Opção inválida no arquivo." }, 400);
      const a = groups.get(o.asset) || [];
      a.push(o);
      groups.set(o.asset, a);
    }
    const timestamp = new Date().toISOString();
    await env.DB.batch(
      [...groups].map(([asset, options]) =>
        env.DB.prepare(
          "INSERT INTO market_snapshots(snapshot_kind,symbol,payload,updated_at) VALUES('chain',?,?,?) ON CONFLICT(snapshot_kind,symbol) DO UPDATE SET payload=excluded.payload,updated_at=excluded.updated_at",
        ).bind(
          asset,
          JSON.stringify({
            asset,
            opportunities: options,
            fetched_at: timestamp,
            source: body.source || "csv",
          }),
          timestamp,
        ),
      ),
    );
    return output({ ok: true, imported: body.opportunities.length });
  }
  if (path === "/api/market/chains" && request.method === "GET") {
    const rows = await env.DB.prepare(
      "SELECT payload FROM market_snapshots WHERE snapshot_kind = 'chain'",
    ).all();
    return output({ chains: rows.results.map((x) => JSON.parse(x.payload)) });
  }
  const chain = path.match(/^\/api\/market\/chain\/([A-Z0-9]{4,12})$/);
  if (chain && request.method === "GET") {
    const symbol = chain[1];
    if (!env.SLDX_API_TOKEN)
      return output(
        {
          error:
            "A chave SLDX precisa ser configurada. Você também pode atualizar pela B3 ou importar CSV.",
        },
        503,
      );
    return output(
      await cache(
        env,
        "chain",
        symbol,
        async () => {
          const [data, summary] = await Promise.all([
            upstream(
              `https://api.sldx.com.br/stock-options-chain/${symbol}`,
              env.SLDX_API_TOKEN,
            ),
            upstream(
              `https://api.sldx.com.br/stock-options/${symbol}`,
              env.SLDX_API_TOKEN,
            ),
          ]);
          const spot = numeric(data.result?.underlying_price),
            tradeDate = /^\d{4}-\d{2}-\d{2}$/.test(summary.trade_date || "")
              ? summary.trade_date
              : null;
          if (!(spot > 0) || !Array.isArray(data.result?.options))
            throw Error("Cadeia de opções incompleta.");
          const opportunities = data.result.options
            .filter(
              (o) =>
                ["PUT", "CALL"].includes(o.type) &&
                /^\d{4}-\d{2}-\d{2}$/.test(o.expiration_date) &&
                o.expiration_date >= date() &&
                numeric(o.strike) > 0 &&
                numeric(o.last_price) >= 0,
            )
            .map((o) => ({
              asset: symbol,
              option_code: String(o.symbol).toUpperCase(),
              option_type: o.type,
              expiry: o.expiration_date,
              spot_price: spot,
              strike: numeric(o.strike),
              premium: numeric(o.last_price),
              bid: numeric(o.bid) > 0 ? numeric(o.bid) : null,
              ask: numeric(o.ask) > 0 ? numeric(o.ask) : null,
              liquidity: numeric(o.volume),
              implied_volatility:
                numeric(o.implied_volatility) > 0
                  ? numeric(o.implied_volatility) / 100
                  : null,
              timestamp: tradeDate,
              source: "sldx_api",
              data_confidence: 0.95,
            }));
          if (!opportunities.length)
            throw Error("Nenhuma opção vigente retornada.");
          return {
            asset: symbol,
            opportunities,
            fetched_at: new Date().toISOString(),
            source: "sldx_api",
            trade_date: tradeDate,
          };
        },
        300000,
      ),
    );
  }
  const history = path.match(/^\/api\/market\/history\/([A-Z0-9]{4,12})$/);
  if (history && request.method === "GET") {
    const symbol = history[1];
    return output(
      await cache(
        env,
        "history",
        symbol,
        async () => {
          const payload = await upstream(
            `https://query1.finance.yahoo.com/v8/finance/chart/${symbol}.SA?range=6mo&interval=1d`,
          );
          const result = payload.chart?.result?.[0],
            closes = (result?.indicators?.quote?.[0]?.close || []).filter(
              (v) => numeric(v) > 0,
            );
          if (closes.length < 30)
            throw Error("Histórico insuficiente para estimar volatilidade.");
          return {
            asset: symbol,
            closes,
            spot: numeric(result.meta?.regularMarketPrice),
            quoted_at: result.meta?.regularMarketTime
              ? new Date(result.meta.regularMarketTime * 1000).toISOString()
              : null,
            fetched_at: new Date().toISOString(),
            source: "Yahoo Finance",
          };
        },
        1800000,
      ),
    );
  }
  // Large public ZIPs are streamed unchanged; decompression/analysis run in the
  // browser, preserving the Worker Free CPU budget and identifying the source.
  if (path === "/api/market/cvm" && request.method === "GET") {
    const year = Number(
      url.searchParams.get("year") || Number(date().slice(0, 4)) - 1,
    );
    if (
      !Number.isInteger(year) ||
      year < 2020 ||
      year > Number(date().slice(0, 4))
    )
      return output({ error: "Ano inválido." }, 400);
    const r = await fetch(
      `https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_${year}.zip`,
      { signal: AbortSignal.timeout(45000) },
    );
    if (!r.ok)
      return output({ error: `CVM indisponível (HTTP ${r.status}).` }, 502);
    return new Response(r.body, {
      headers: {
        "Content-Type": "application/zip",
        "Cache-Control": "private, max-age=3600",
        "X-Data-Source": "CVM DFP",
      },
    });
  }
  if (path === "/api/market/b3" && request.method === "GET") {
    const day = url.searchParams.get("date");
    if (!/^\d{4}-\d{2}-\d{2}$/.test(day || "") || day > date())
      return output({ error: "Data de pregão inválida." }, 400);
    const [y, m, d] = day.split("-");
    const r = await fetch(
      `https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_D${d}${m}${y}.ZIP`,
      { signal: AbortSignal.timeout(20000) },
    );
    if (!r.ok)
      return output(
        { error: `B3 sem arquivo para ${day} (HTTP ${r.status}).` },
        502,
      );
    return new Response(r.body, {
      headers: {
        "Content-Type": "application/zip",
        "Cache-Control": "private, max-age=3600",
        "X-Data-Source": "B3 COTAHIST",
      },
    });
  }
  return null;
}
