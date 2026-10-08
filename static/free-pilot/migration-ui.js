(function (root) {
  "use strict";
  const D = root.FMDomain,
    $ = (s) => document.querySelector(s),
    A = () => root.FMApp;
  let state = {},
    market = { chains: [], profiles: {}, universe: [], history: new Map() },
    initialization,
    refreshing = false;
  const empty = (text) => `<p class="migration-empty">${A().escape(text)}</p>`;
  const pct = (v) =>
    v === null || v === undefined
      ? "—"
      : `${(v * 100).toFixed(2).replace(".", ",")}%`;
  const source = (o) =>
    `${o.source || "Fonte não informada"} · referência ${o.timestamp || o.trade_date || "não informada"}`;
  function options() {
    return market.chains
      .flatMap((c) => c.opportunities || [])
      .filter((o) => D.days(o.expiry) >= 0);
  }
  function holdings() {
    const map = new Map();
    for (const lot of state.equities || []) {
      const q = Math.max(0, D.n(lot.available_quantity ?? lot.quantity)),
        original = Math.max(0, D.n(lot.quantity)),
        cost =
          D.n(lot.tax_cost_total ?? lot.cash_cost_total) *
          (original ? q / original : 0);
      const row = map.get(lot.asset) || {
        asset: lot.asset,
        quantity: 0,
        cost: 0,
        covered: 0,
      };
      row.quantity += q;
      row.cost += cost;
      map.set(lot.asset, row);
    }
    const size = A().cfg("Tamanho contrato opcoes", 100);
    for (const op of state.operations || [])
      if (op.tipo === "CALL" && /venda|coberta/i.test(op.estrategia)) {
        const pref = (state.operation_preferences || []).find(
          (p) => String(p.operation_id) === String(op.id),
        );
        const asset =
          pref?.underlying_asset ||
          market.universe.find((u) => op.ativo.startsWith(u.root))?.asset;
        const row = map.get(asset);
        if (row) row.covered += D.n(op.contratos) * size;
      }
    return [...map.values()]
      .filter((h) => h.quantity > 0)
      .map((h) => ({
        ...h,
        available_quantity: Math.max(0, h.quantity - h.covered),
        average: h.cost / h.quantity,
      }));
  }
  function card(title, fields, note, status = "watchlist", details = "") {
    return `<article class="migration-card"><header><h3>${A().escape(title)}</h3><span class="migration-status migration-status--${status}">${{ eligible: "Elegível", watchlist: "Atenção", ineligible: "Bloqueada", insufficient_data: "Dados insuficientes" }[status] || A().escape(status)}</span></header><dl>${fields.map(([k, v]) => `<div><dt>${A().escape(k)}</dt><dd>${A().escape(v)}</dd></div>`).join("")}</dl><p>${A().escape(note)}</p>${details}</article>`;
  }
  function renderRadar() {
    const form = $("#radar-filters"),
      filter = Object.fromEntries(new FormData(form)),
      current = new Set((state.operations || []).map((x) => x.ativo)),
      h = holdings();
    const capital =
      h.reduce((s, x) => s + x.cost, 0) +
      (state.operations || [])
        .filter((x) => x.tipo === "PUT")
        .reduce(
          (s, x) =>
            s +
            D.n(x.strike) *
              D.n(x.contratos) *
              A().cfg("Tamanho contrato opcoes", 100),
          0,
        );
    const policy = {
      min_roi: D.n(filter.roi) / 100,
      min_days: D.n(filter.min_days),
      max_days: D.n(filter.max_days),
    };
    const rows = D.rank(
      options()
        .filter(
          (o) =>
            o.option_type === "PUT" &&
            !current.has(o.option_code) &&
            (!filter.asset || o.asset === filter.asset.trim().toUpperCase()),
        )
        .map((o) => {
          const own = h.find((x) => x.asset === o.asset)?.cost || 0,
            extra = D.n(o.strike) * 100;
          const profile = {
            ...market.profiles[o.asset],
            concentration_pct: capital
              ? (own + extra) / (capital + extra)
              : null,
          };
          return D.assess(o, profile, policy);
        }),
    ).filter((o) => filter.status === "all" || o.status === filter.status);
    $("#opportunity-cards").innerHTML =
      rows
        .slice(0, 120)
        .map((o) => {
          const m = o.metrics,
            details = `<details><summary>Ver fatores e riscos</summary><p>${A().escape([...o.blockers, ...o.warnings].join(" · ") || "Filtros atendidos.")}</p><p>${A().escape(o.profile?.positive_notes?.join(" · ") || "Qualidade fundamental ainda não confirmada.")}</p>${o.score === null ? "" : `<p>Qualidade ${o.components.quality.toFixed(1)} · Segurança ${o.components.safety.toFixed(1)} · ROI ${o.components.roi.toFixed(1)} · Preço ${o.components.price.toFixed(1)} · Capital ${o.components.capital.toFixed(1)}</p>`}<p>Qualidade: ${A().escape(o.profile?.source || "não informada")}, ano ${A().escape(o.profile?.reference_year || "—")}; concentração projetada ${pct(o.profile?.concentration_pct)}</p></details>`;
          return card(
            `${o.asset} · ${o.option_code}`,
            [
              ["ROI bruto", pct(m?.roi)],
              ["Preço líquido", m ? A().money(m.net_price) : "—"],
              ["Desconto", pct(m?.discount)],
              ["Score", o.score === null ? "—" : `${o.score}/100`],
              ["Vencimento", o.expiry],
              ["Prazo", `${m?.dte ?? "—"} dias`],
            ],
            source(o),
            o.status,
            details,
          );
        })
        .join("") ||
      empty(
        "Nenhuma nova PUT com os filtros atuais. Atualize o mercado ou ajuste os filtros.",
      );
  }
  function renderScanner() {
    const rows = D.coveredCalls(options(), holdings());
    $("#scanner-cards").innerHTML =
      rows
        .slice(0, 80)
        .map((o) =>
          card(
            `${o.asset} · ${o.option_code}`,
            [
              ["Prêmio / ação", A().money(o.premium)],
              ["Venda efetiva", A().money(o.metrics.effective_sale)],
              ["Saldo livre", `${o.available_quantity} ações`],
              ["Contratos livres", String(o.contracts)],
              ["Vencimento", o.expiry],
              ["Score scanner", String(o.score)],
            ],
            `${source(o)}${o.replacement_required ? " · Exige encerrar ou substituir a cobertura existente." : ""}`,
            o.replacement_required ? "watchlist" : "eligible",
          ),
        )
        .join("") ||
      empty(
        "Nenhuma CALL adequada à carteira no mercado carregado. Consulte as ações da carteira para atualizar.",
      );
  }
  function renderJade() {
    const rows = D.jade(options());
    $("#jade-cards").innerHTML =
      rows
        .map((o) =>
          card(
            o.asset,
            [
              ["Vende PUT", o.put.option_code],
              ["Vende CALL", o.short.option_code],
              ["Compra CALL", o.long.option_code],
              ["Crédito / ação", A().money(o.credit)],
              ["Equilíbrio", A().money(o.break_even)],
              ["Perda máxima / lote", A().money(o.max_loss)],
              ["Largura do spread", A().money(o.width)],
              ["Vencimento", o.expiry],
            ],
            `Referência: ${source(o.put)}. Crédito ≥ spread elimina o prejuízo no lado da alta, antes de custos. O risco de queda permanece.`,
            "watchlist",
          ),
        )
        .join("") ||
      empty(
        "Nenhuma combinação atende aos filtros com bid/ask e liquidez reais. Atualize o mercado; nenhuma opção é simulada como se fosse cotação.",
      );
  }
  function renderTax() {
    const rows = D.taxProjection(state.closed || [], state.darfs || []),
      e = A().escape,
      m = A().money;
    $("#tax-result").textContent = m(
      rows.reduce((s, r) => s + r.common_result + r.day_result, 0),
    );
    $("#tax-estimate").textContent = m(rows.reduce((s, r) => s + r.pending, 0));
    $("#tax-paid").textContent = m(
      (state.darfs || []).reduce((s, p) => s + D.n(p.amount), 0),
    );
    $("#tax-month-rows").innerHTML = rows
      .slice()
      .reverse()
      .map(
        (r) =>
          `<tr class="tax-memory-row"><td><strong>${e(r.competence)}</strong><small>Vence ${e(r.due_date.split("-").reverse().join("/"))}</small></td><td>${m(r.common_result)}<small>Day trade ${m(r.day_result)}</small></td><td>${m(r.common_loss_compensated + r.day_loss_compensated)}<small>Saldo comum ${m(r.common_loss_carry)} · DT ${m(r.day_loss_carry)}</small></td><td>${m(r.irrf_deducted)}</td><td><strong>${m(r.estimated_darf)}</strong><small>Acumulado ${m(r.tax_carry)}</small></td><td>${m(r.paid)}<small>Pendente ${m(r.pending)}</small></td><td>${e(r.status)}${r.deferred_count ? `<small>${r.deferred_count} PUT(s): custo incorporado às ações</small>` : ""}${r.review_count ? `<small>${r.review_count} exercício(s) a revisar</small>` : ""}</td></tr>`,
      )
      .join("");
  }
  function renderRoll() {
    const field = $("#roll-simulation-form").elements.operation,
      old = field.value;
    field.innerHTML = (state.operations || [])
      .map(
        (o) =>
          `<option value="${o.id}">${A().escape(o.ativo)} · ${A().escape(o.tipo)}</option>`,
      )
      .join("");
    if ([...field.options].some((o) => o.value === old)) field.value = old;
  }
  async function initialize() {
    const results = await Promise.allSettled([
      A().request("/market/status"),
      A().request("/market/chains"),
      A().request("/market/profiles"),
    ]);
    for (let i = 0; i < results.length; i++) {
      const r = results[i];
      if (r.status === "rejected") {
        A().showMessage(r.reason.message, "error");
        continue;
      }
      const data = await r.value.json();
      if (i === 0) {
        market.universe = data.universe;
        $("#market-message").textContent = data.sldx_configured
          ? "SLDX disponível. B3, CVM e CSV também podem ser usados."
          : "SLDX ainda sem chave. Atualize pela B3 ou importe CSV.";
      }
      if (i === 1) market.chains = data.chains;
      if (i === 2) market.profiles = data.profiles;
    }
    decorate(state);
    A().render();
    render(state);
  }
  function render(data) {
    state = data;
    renderTax();
    renderRadar();
    renderScanner();
    renderJade();
    renderRoll();
    if (!initialization)
      initialization = initialize().catch((error) =>
        A().showMessage(error.message, "error"),
      );
  }
  function decorate(data) {
    const quotes = new Map(
      (data.api_market_quotes || []).map((q) => [
        q.quote_kind + ":" + q.symbol,
        q,
      ]),
    );
    for (const c of market.chains)
      for (const o of c.opportunities || []) {
        quotes.set("option:" + o.option_code, {
          quote_kind: "option",
          symbol: o.option_code,
          price: o.premium,
          source: o.source,
          quoted_at: o.timestamp || c.fetched_at,
        });
        quotes.set("stock:" + o.asset, {
          quote_kind: "stock",
          symbol: o.asset,
          price: o.spot_price,
          source: o.source,
          quoted_at: o.timestamp || c.fetched_at,
        });
      }
    for (const [asset, h] of market.history)
      if (h.spot > 0)
        quotes.set("stock:" + asset, {
          quote_kind: "stock",
          symbol: asset,
          price: h.spot,
          source: h.source,
          quoted_at: h.quoted_at || h.fetched_at,
        });
    data.api_market_quotes = [...quotes.values()];
  }
  async function refresh(symbols, message) {
    if (refreshing) return;
    refreshing = true;
    message.textContent = "Consultando fontes de mercado…";
    const failures = [];
    try {
      for (const asset of symbols) {
        try {
          const chain = await (
            await A().request("/market/chain/" + asset)
          ).json();
          market.chains = market.chains
            .filter((c) => c.asset !== asset)
            .concat(chain);
          if (chain.warning) failures.push(asset + ": " + chain.warning);
        } catch (error) {
          failures.push(asset + ": " + error.message);
        }
        try {
          const history = await (
            await A().request("/market/history/" + asset)
          ).json();
          market.history.set(asset, history);
        } catch (error) {
          failures.push(asset + " histórico: " + error.message);
        }
      }
      decorate(state);
      A().render();
      render(state);
      A().updateNewOperationPreview();
      message.textContent = failures.length
        ? "Atualização parcial: " + failures.join(" · ")
        : "Mercado atualizado. Confira a data de referência nos resultados.";
    } finally {
      refreshing = false;
    }
  }
  async function unpack(kind, response) {
    const buffer = await response.arrayBuffer();
    if (buffer.byteLength > 75 * 1024 * 1024)
      throw Error("Arquivo de mercado excede 75 MB.");
    return new Promise((resolve, reject) => {
      const worker = new Worker("free-pilot/market-data-worker.mjs?v=1", {
        type: "module",
      });
      worker.onmessage = ({ data }) => {
        worker.terminate();
        data.ok ? resolve(data.result) : reject(Error(data.error));
      };
      worker.onerror = () => {
        worker.terminate();
        reject(Error("Não foi possível processar o arquivo de mercado."));
      };
      worker.postMessage(
        {
          kind,
          buffer,
          universe: market.universe,
          year: Number(D.today().slice(0, 4)) - 1,
          asOf: D.today(),
        },
        [buffer],
      );
    });
  }
  async function importOptions(opportunities, source) {
    if (!opportunities.length)
      throw Error("Fonte sem opções vigentes para os ativos cadastrados.");
    await A().request("/market/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ opportunities, source }),
    });
    market.chains = (await (await A().request("/market/chains")).json()).chains;
    decorate(state);
    A().render();
    render(state);
  }
  $("#market-refresh").onclick = () => {
    const symbols = [
      ...new Set(
        $("#market-symbols")
          .value.toUpperCase()
          .split(/[,;\s]+/)
          .filter(Boolean),
      ),
    ];
    if (
      !symbols.length ||
      symbols.length > 15 ||
      symbols.some((s) => !/^[A-Z0-9]{4,12}$/.test(s))
    ) {
      $("#market-message").textContent =
        "Informe de 1 a 15 códigos de ações válidos.";
      return;
    }
    refresh(symbols, $("#market-message")).catch((error) =>
      A().showMessage(error.message, "error"),
    );
  };
  $("#scanner-refresh").onclick = () =>
    refresh(
      holdings().map((h) => h.asset),
      $("#scanner-message"),
    ).catch((error) => A().showMessage(error.message, "error"));
  $("#radar-filters").oninput = renderRadar;
  $("#radar-filters").onsubmit = (e) => e.preventDefault();
  $("#jade-refresh").onclick = renderJade;
  $("#roll-simulation-form").onsubmit = (e) => {
    e.preventDefault();
    const form = e.currentTarget,
      op = (state.operations || []).find(
        (o) => String(o.id) === form.elements.operation.value,
      );
    if (!op) return;
    const pref = (state.operation_preferences || []).find(
        (p) => String(p.operation_id) === String(op.id),
      ),
      asset =
        pref?.underlying_asset ||
        market.universe.find((u) => op.ativo.startsWith(u.root))?.asset;
    const rows = D.roll(
      { ...op, asset },
      options(),
      form.elements.repurchase.value,
      D.n(op.contratos) * A().cfg("Tamanho contrato opcoes", 100),
    );
    $("#roll-cards").innerHTML =
      rows
        .slice(0, 60)
        .map((o) =>
          card(
            o.option_code,
            [
              ["Novo strike", A().money(o.strike)],
              ["Crédito / débito", A().money(o.net_credit)],
              ["Dias adicionais", String(o.extra_days)],
              ["Novo vencimento", o.expiry],
            ],
            `${source(o)} · Crédito usa bid, quando disponível; custos não incluídos.`,
            "watchlist",
          ),
        )
        .join("") ||
      empty(
        "Nenhuma alternativa posterior ao vencimento atual no mercado carregado.",
      );
  };
  $("#market-csv").onchange = async (e) => {
    try {
      const file = e.target.files[0];
      if (!file) return;
      if (file.size > 5 * 1024 * 1024)
        throw Error("CSV deve ter no máximo 5 MB.");
      const result = D.csv(await file.text());
      await importOptions(result.opportunities, "csv");
      $("#market-message").textContent =
        `${result.opportunities.length} opções importadas; ${result.rejected_rows.length} linhas rejeitadas.`;
    } catch (error) {
      A().showMessage(error.message, "error");
    } finally {
      e.target.value = "";
    }
  };
  $("#market-cvm").onclick = async (e) => {
    e.target.disabled = true;
    $("#market-message").textContent =
      "Baixando demonstrações públicas da CVM e calculando qualidade…";
    try {
      const profiles = await unpack("cvm", await A().request("/market/cvm"));
      await A().request("/market/profiles", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profiles }),
      });
      market.profiles = Object.fromEntries(profiles.map((p) => [p.asset, p]));
      renderRadar();
      $("#market-message").textContent =
        `Qualidade CVM atualizada para ${profiles.length} ativos. Consulte fatores e dados ausentes nos cards.`;
    } catch (error) {
      A().showMessage(error.message, "error");
      $("#market-message").textContent = error.message;
    } finally {
      e.target.disabled = false;
    }
  };
  $("#market-b3").onclick = async (e) => {
    e.target.disabled = true;
    try {
      let loaded = false,
        lastError;
      for (let offset = 0; offset < 7; offset++) {
        const date = new Date(D.today() + "T12:00:00Z");
        date.setUTCDate(date.getUTCDate() - offset);
        if ([0, 6].includes(date.getUTCDay())) continue;
        const day = date.toISOString().slice(0, 10);
        $("#market-message").textContent = "Consultando COTAHIST da B3: " + day;
        try {
          const response = await A().request("/market/b3?date=" + day),
            rows = await unpack("b3", response);
          await importOptions(rows, "b3_cotahist");
          $("#market-message").textContent =
            `B3 atualizada: ${rows.length} opções, pregão ${day}.`;
          loaded = true;
          break;
        } catch (error) {
          lastError = error;
        }
      }
      if (!loaded) throw lastError || Error("B3 indisponível nesta semana.");
    } catch (error) {
      A().showMessage(error.message, "error");
      $("#market-message").textContent = error.message;
    } finally {
      e.target.disabled = false;
    }
  };
  $("#tax-print").onclick = () => {
    document.body.classList.add("fm-tax-print");
    window.print();
  };
  window.addEventListener("afterprint", () =>
    document.body.classList.remove("fm-tax-print"),
  );
  root.FMMigration = {
    render,
    decorate,
    historyFor: (asset) => market.history.get(asset),
    optionFor: (code) => options().find((o) => o.option_code === code),
  };
})(globalThis);
