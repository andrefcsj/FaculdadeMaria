/* Deterministic calculations shared by browser and isolated migration tests.
 * Rules are ported from engine/metrics, filters, score, and the fiscal service.
 * Providers and persistence deliberately live outside this module. */
(function (root) {
  "use strict";
  const numeric = (value) => {
    if (
      value === null ||
      value === undefined ||
      value === "" ||
      typeof value === "boolean"
    )
      return null;
    const raw = String(value).replace(/R\$|\s/g, "");
    const n = Number(
      raw.includes(",") ? raw.replace(/\./g, "").replace(",", ".") : raw,
    );
    return Number.isFinite(n) ? n : null;
  };
  const n = (value) => numeric(value) ?? 0;
  const cents = (value) => Math.round((value + Number.EPSILON) * 100) / 100;
  const clamp = (value) => Math.max(0, Math.min(1, value));
  const today = () =>
    new Intl.DateTimeFormat("sv-SE", { timeZone: "America/Sao_Paulo" }).format(
      new Date(),
    );
  function dateValue(value) {
    let s = String(value || "").slice(0, 10);
    if (/^\d{2}\/\d{2}\/\d{4}$/.test(s)) s = s.split("/").reverse().join("-");
    if (
      !/^\d{4}-\d{2}-\d{2}$/.test(s) ||
      !Number.isFinite(Date.parse(s + "T12:00:00Z"))
    )
      return null;
    return new Date(s + "T12:00:00Z").toISOString().slice(0, 10) === s
      ? s
      : null;
  }
  const days = (expiry, asOf = today()) =>
    dateValue(expiry) && dateValue(asOf)
      ? Math.round(
          (Date.parse(dateValue(expiry)) - Date.parse(asOf)) / 86400000,
        )
      : null;
  const shiftMonth = (month, offset) => {
    const [y, m] = month.split("-").map(Number);
    return new Date(Date.UTC(y, m - 1 + offset, 1)).toISOString().slice(0, 7);
  };
  function probability(type, spot, strike, dte, vol) {
    spot = numeric(spot);
    strike = numeric(strike);
    vol = numeric(vol);
    if (
      !["PUT", "CALL"].includes(type) ||
      !(spot > 0) ||
      !(strike > 0) ||
      dte === null ||
      dte < 0
    )
      return null;
    if (dte === 0)
      return spot === strike
        ? 0.5
        : type === "PUT"
          ? Number(spot < strike)
          : Number(spot > strike);
    if (!(vol > 0)) return null;
    const t = dte / 365,
      z =
        (Math.log(strike / spot) + 0.5 * vol * vol * t) / (vol * Math.sqrt(t));
    // Abramowitz–Stegun 7.1.26, absolute error < 1.5e-7.
    const x = Math.abs(z) / Math.SQRT2,
      a = 1 / (1 + 0.3275911 * x);
    const erf =
      1 -
      ((((1.061405429 * a - 1.453152027) * a + 1.421413741) * a - 0.284496736) *
        a +
        0.254829592) *
        a *
        Math.exp(-x * x);
    const put = 0.5 * (1 + (z < 0 ? -erf : erf));
    return clamp(type === "PUT" ? put : 1 - put);
  }
  function historicalVolatility(closes) {
    const values = closes.map(numeric).filter((v) => v > 0);
    if (values.length < 30) return null;
    const returns = values.slice(1).map((v, i) => Math.log(v / values[i]));
    const mean = returns.reduce((s, v) => s + v, 0) / returns.length;
    const vol =
      Math.sqrt(
        returns.reduce((s, v) => s + (v - mean) ** 2, 0) / (returns.length - 1),
      ) * Math.sqrt(252);
    return Number.isFinite(vol) && vol > 0 ? vol : null;
  }
  function metrics(o, { asOf = today(), quantity = 100, costs = null } = {}) {
    const spot = numeric(o.spot_price),
      strike = numeric(o.strike),
      premium = numeric(o.premium),
      dte = days(o.expiry, asOf);
    if (
      !(spot > 0) ||
      !(strike > 0) ||
      premium === null ||
      premium < 0 ||
      dte === null ||
      dte < 0 ||
      !(quantity > 0)
    )
      return null;
    return {
      net_price: strike - premium,
      discount: (spot - strike + premium) / spot,
      roi: premium / strike,
      net_roi:
        costs === null
          ? null
          : (premium * quantity - n(costs)) / (strike * quantity),
      distance: (spot - strike) / spot,
      dte,
      annualized_roi: dte ? ((premium / strike) * 365) / dte : null,
      premium_total: premium * quantity,
      capital: strike * quantity,
      effective_sale: strike + premium,
    };
  }
  function assess(o, profile = {}, policy = {}, asOf = today()) {
    const m = metrics(o, { asOf }),
      blockers = [],
      warnings = [];
    if (!m)
      return {
        ...o,
        metrics: null,
        status: "insufficient_data",
        score: null,
        blockers: ["Cotação, strike, prêmio ou vencimento inválido."],
        warnings: [],
      };
    const add = (list, condition, text) => {
      if (condition) list.push(text);
    };
    const liquidity = numeric(o.liquidity),
      bid = numeric(o.bid),
      ask = numeric(o.ask),
      spread = bid > 0 && ask >= bid ? (ask - bid) / ((bid + ask) / 2) : null;
    add(blockers, o.option_type !== "PUT", "Análise de PUT exige uma PUT.");
    add(
      blockers,
      m.dte < (policy.min_days ?? 15) || m.dte > (policy.max_days ?? 60),
      "Prazo fora da janela configurada.",
    );
    add(
      blockers,
      m.roi < (policy.min_roi ?? 0.04),
      "ROI abaixo do mínimo configurado.",
    );
    add(
      blockers,
      !policy.allow_itm && n(o.strike) > n(o.spot_price),
      "Strike da PUT acima da cotação.",
    );
    add(
      blockers,
      liquidity !== null && liquidity < (policy.min_liquidity ?? 10000),
      "Liquidez abaixo do mínimo.",
    );
    add(warnings, liquidity === null, "Liquidez não informada.");
    add(
      blockers,
      spread !== null && spread > (policy.max_spread ?? 0.25),
      "Spread acima do limite.",
    );
    add(
      warnings,
      spread === null,
      "Bid/ask insuficientes para avaliar o spread.",
    );
    add(
      blockers,
      profile.assignment_eligible === false,
      "Ativo não aprovado para exercício.",
    );
    add(
      blockers,
      profile.long_term_suitable === false,
      "Ativo não aprovado para longo prazo.",
    );
    add(
      blockers,
      (profile.blocking_events || []).length > 0,
      (profile.blocking_events || []).join(" · "),
    );
    const quality = numeric(profile.quality_score);
    add(
      blockers,
      quality !== null && quality < 0.6,
      "Qualidade abaixo do mínimo.",
    );
    add(
      warnings,
      quality !== null && quality >= 0.6 && quality < 0.75,
      "Qualidade aceitável, com pontos de atenção.",
    );
    add(
      warnings,
      numeric(profile.data_confidence) === null ||
        n(profile.data_confidence) < 0.5,
      "Confiança da qualidade insuficiente.",
    );
    add(
      blockers,
      numeric(profile.concentration_pct) !== null &&
        n(profile.concentration_pct) > (policy.max_concentration ?? 0.35),
      "Concentração projetada acima do limite.",
    );
    const ref = String(o.timestamp || o.quoted_at || "").slice(0, 10),
      age = days(asOf, ref);
    add(
      warnings,
      age === null || age > 3,
      "Data de mercado ausente ou defasada.",
    );
    const missingQuality =
      quality === null ||
      profile.assignment_eligible == null ||
      profile.long_term_suitable == null;
    add(warnings, missingQuality, "Qualidade incompleta: score indisponível.");
    const safety = liquidity === null || spread === null ? 0.55 : 1;
    const components = {
      quality: 30 * (quality ?? 0),
      safety: 25 * safety,
      roi: 20 * clamp(m.roi / (policy.target_roi ?? 0.04)),
      price: 15 * clamp(m.discount / 0.05),
      capital: 10 * clamp(m.roi / (policy.target_roi ?? 0.04)),
    };
    const score =
      blockers.length || missingQuality
        ? null
        : Math.round(Object.values(components).reduce((s, v) => s + v, 0));
    const status = blockers.length
      ? "ineligible"
      : missingQuality
        ? "insufficient_data"
        : warnings.length
          ? "watchlist"
          : "eligible";
    return {
      ...o,
      metrics: m,
      spread,
      score,
      components,
      status,
      blockers,
      warnings,
      profile,
    };
  }
  function rank(items) {
    const priority = {
      eligible: 4,
      watchlist: 3,
      insufficient_data: 2,
      ineligible: 1,
    };
    return items
      .slice()
      .sort(
        (a, b) =>
          (priority[b.status] || 0) - (priority[a.status] || 0) ||
          (b.score ?? 0) - (a.score ?? 0) ||
          n(b.profile?.data_confidence) - n(a.profile?.data_confidence) ||
          n(b.metrics?.discount) - n(a.metrics?.discount) ||
          String(a.option_code).localeCompare(String(b.option_code)),
      );
  }
  function csv(text, asOf = today()) {
    const first = String(text)
      .replace(/^\uFEFF/, "")
      .split(/\r?\n/)[0];
    const delimiter = [";", ",", "\t", "|"].sort(
      (a, b) => first.split(b).length - first.split(a).length,
    )[0];
    const rows = [],
      row = [];
    let value = "",
      quoted = false;
    for (let i = 0; i <= text.length; i++) {
      const c = text[i] ?? "\n";
      if (c === '"') {
        if (quoted && text[i + 1] === '"') {
          value += '"';
          i++;
        } else quoted = !quoted;
      } else if (!quoted && (c === delimiter || c === "\n")) {
        row.push(value.replace(/\r$/, ""));
        value = "";
        if (c === "\n") {
          if (row.some(Boolean)) rows.push(row.splice(0));
          else row.length = 0;
        }
      } else value += c;
    }
    if (quoted) throw Error("CSV com aspas não fechadas.");
    const norm = (v) =>
      String(v)
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLowerCase()
        .replace(/[^a-z0-9]/g, "");
    const aliases = {
      option_code: ["optioncode", "opcao", "codigoopcao", "codigodaopcao"],
      asset: ["asset", "ativo", "acao", "ticker", "underlying"],
      option_type: ["optiontype", "tipo", "tipodeopcao"],
      expiry: ["expiry", "vencimento", "expirationdate"],
      spot_price: [
        "spotprice",
        "spot",
        "cotacao",
        "precoativo",
        "underlyingprice",
      ],
      strike: ["strike", "exercicio", "precoexercicio"],
      premium: ["premium", "premio", "precoopcao", "ultimo", "lastprice"],
      bid: ["bid", "compra"],
      ask: ["ask", "venda"],
      liquidity: ["liquidity", "volume", "liquidez"],
      timestamp: ["timestamp", "data", "datareferencia", "quotedat"],
    };
    const header = (rows.shift() || []).map(norm),
      columns = {};
    for (const [key, names] of Object.entries(aliases))
      columns[key] = header.findIndex((h) => names.includes(h));
    for (const key of [
      "option_code",
      "asset",
      "expiry",
      "spot_price",
      "strike",
      "premium",
    ])
      if (columns[key] < 0) throw Error(`Coluna obrigatória ausente: ${key}.`);
    const accepted = [],
      rejected = [];
    rows.forEach((row, i) => {
      const o = Object.fromEntries(
        Object.entries(columns).map(([k, j]) => [k, j >= 0 ? row[j] : null]),
      );
      o.option_code = String(o.option_code || "").toUpperCase();
      o.asset = String(o.asset || "").toUpperCase();
      o.option_type = String(o.option_type || "PUT").toUpperCase();
      o.expiry = dateValue(o.expiry);
      o.source = "csv";
      for (const k of [
        "spot_price",
        "strike",
        "premium",
        "bid",
        "ask",
        "liquidity",
      ])
        o[k] = numeric(o[k]);
      if (
        !/^[A-Z0-9]{4,20}$/.test(o.option_code) ||
        !/^[A-Z0-9]{4,12}$/.test(o.asset) ||
        !["PUT", "CALL"].includes(o.option_type) ||
        !metrics(o, { asOf })
      )
        rejected.push(i + 2);
      else accepted.push(o);
    });
    if (!accepted.length)
      throw Error(
        "Nenhuma opção válida no CSV. Confira as datas e os valores.",
      );
    return { opportunities: accepted, rejected_rows: rejected };
  }
  function coveredCalls(options, holdings, asOf = today()) {
    const portfolio = new Map(holdings.map((x) => [x.asset, x]));
    return options
      .filter((o) => o.option_type === "CALL")
      .map((o) => {
        const h = portfolio.get(o.asset),
          m = metrics(o, { asOf });
        if (
          !h ||
          !m ||
          m.dte < 1 ||
          m.dte > 45 ||
          n(o.premium) <= 0 ||
          n(o.strike) < Math.max(n(h.average), n(o.spot_price)) ||
          n(h.quantity) < 100
        )
          return null;
        const available = n(h.available_quantity),
          score = Math.trunc(
            Math.min(
              100,
              Math.max(
                0,
                (((n(o.premium) / n(o.spot_price)) * 365) / m.dte) * 120 +
                  (n(o.strike) / n(o.spot_price) - 1) * 180 +
                  Math.min(n(o.liquidity) / 50000, 1) * 20,
              ),
            ),
          );
        return {
          ...o,
          metrics: m,
          score,
          quantity: h.quantity,
          available_quantity: available,
          contracts: Math.floor(available / 100),
          replacement_required: available < 100,
        };
      })
      .filter(Boolean)
      .sort(
        (a, b) =>
          b.score - a.score ||
          a.metrics.dte - b.metrics.dte ||
          a.option_code.localeCompare(b.option_code),
      );
  }
  function jade(options, asOf = today()) {
    // Only actual option symbols and quotes; no projected symbols or invented IV.
    const result = [],
      groups = new Map();
    for (const o of options) {
      const dte = days(o.expiry, asOf);
      if (dte < 15 || dte > 45) continue;
      const key = o.asset + ":" + o.expiry;
      const group = groups.get(key) || [];
      group.push(o);
      groups.set(key, group);
    }
    for (const group of groups.values()) {
      const puts = group.filter(
        (o) =>
          o.option_type === "PUT" &&
          n(o.strike) < n(o.spot_price) &&
          n(o.bid) > 0,
      );
      const calls = group
        .filter(
          (o) => o.option_type === "CALL" && n(o.strike) > n(o.spot_price),
        )
        .sort((a, b) => n(a.strike) - n(b.strike));
      for (const put of puts.slice(0, 100))
        for (let i = 0; i < calls.length - 1; i++)
          for (let j = i + 1; j < Math.min(i + 6, calls.length); j++) {
            const short = calls[i],
              long = calls[j];
            if (!(n(short.bid) > 0) || !(n(long.ask) > 0)) continue;
            const width = n(long.strike) - n(short.strike),
              credit = n(put.bid) + n(short.bid) - n(long.ask);
            if (credit < width || credit <= 0) continue;
            const legs = [put, short, long];
            if (
              legs.some(
                (o) => numeric(o.liquidity) === null || n(o.liquidity) < 1000,
              )
            )
              continue;
            result.push({
              asset: put.asset,
              expiry: put.expiry,
              dte: days(put.expiry, asOf),
              put,
              short,
              long,
              width,
              credit,
              break_even: n(put.strike) - credit,
              max_profit: credit * 100,
              max_loss: Math.max(0, (n(put.strike) - credit) * 100),
              roi: credit / n(put.strike),
              source: put.source,
            });
          }
    }
    return result
      .sort((a, b) => a.max_loss - b.max_loss || b.roi - a.roi)
      .slice(0, 50);
  }
  function roll(
    operation,
    alternatives,
    repurchase,
    quantity = 100,
    asOf = today(),
  ) {
    if (!(numeric(repurchase) >= 0)) return [];
    return alternatives
      .filter(
        (o) =>
          o.option_type === operation.tipo &&
          o.asset === operation.asset &&
          o.option_code !== operation.ativo &&
          o.expiry > operation.vencimento,
      )
      .map((o) => {
        const m = metrics(o, { asOf, quantity });
        if (!m) return null;
        const sell = numeric(o.bid) ?? numeric(o.premium);
        if (sell === null) return null;
        return {
          ...o,
          metrics: m,
          net_credit: (sell - n(repurchase)) * quantity,
          extra_days: days(o.expiry, operation.vencimento),
          strike_change: n(o.strike) - n(operation.strike),
        };
      })
      .filter(Boolean)
      .sort(
        (a, b) => b.net_credit - a.net_credit || a.extra_days - b.extra_days,
      );
  }
  function taxProjection(closed, payments = [], asOf = today()) {
    const monthly = new Map();
    const get = (month) => {
      if (!monthly.has(month))
        monthly.set(month, {
          common_result: 0,
          day_result: 0,
          common_irrf: 0,
          day_irrf: 0,
          review_count: 0,
          deferred_count: 0,
          paid: 0,
        });
      return monthly.get(month);
    };
    for (const o of closed) {
      const close = dateValue(
          o["Data fechamento"] || o.Data_fechamento || o.closed_at,
        ),
        open = dateValue(
          o.data_abertura || o.Data_abertura || o["Data abertura"],
        );
      if (!close) continue;
      const row = get(close.slice(0, 7)),
        type = String(o.tipo || o.Tipo || "").toUpperCase(),
        method = String(
          o.method || o.Metodo_encerramento || o.Observacoes || "",
        ).toLowerCase();
      const exercised = /exerc/.test(method);
      if (exercised && type === "PUT") {
        row.deferred_count++;
        continue;
      }
      if (/cancel/.test(method)) continue;
      if (
        exercised &&
        type === "CALL" &&
        o.exercise_tax_result == null &&
        o.Metodo_encerramento !== "exercida"
      ) {
        row.review_count++;
        continue;
      }
      const result = n(
          o.exercise_tax_result ??
            o.Resultado_final ??
            o.Resultado_realizado ??
            o.resultado_final ??
            o.Lucro_tributavel,
        ),
        irrf = n(o.irrf ?? o.IRRF);
      const modality = open === close ? "day" : "common";
      row[modality + "_result"] += result + irrf;
      row[modality + "_irrf"] += irrf;
    }
    for (const payment of payments)
      if (/^\d{4}-(0[1-9]|1[0-2])$/.test(payment.competence || ""))
        get(payment.competence).paid += n(payment.amount);
    const end = shiftMonth(asOf.slice(0, 7), 1),
      start = [...monthly.keys(), shiftMonth(asOf.slice(0, 7), -1)].sort()[0];
    if (start < "2000-01" || start > end)
      throw Error("Período fiscal inválido.");
    let commonLoss = 0,
      dayLoss = 0,
      commonCredit = 0,
      dayCredit = 0,
      taxCarry = 0;
    const rows = [];
    for (let month = start; month <= end; month = shiftMonth(month, 1)) {
      const d = get(month),
        commonUsed = Math.min(commonLoss, Math.max(0, d.common_result)),
        dayUsed = Math.min(dayLoss, Math.max(0, d.day_result));
      const commonBase = Math.max(0, d.common_result - commonUsed),
        dayBase = Math.max(0, d.day_result - dayUsed);
      commonLoss = commonLoss - commonUsed + Math.max(0, -d.common_result);
      dayLoss = dayLoss - dayUsed + Math.max(0, -d.day_result);
      commonCredit += d.common_irrf;
      dayCredit += d.day_irrf;
      const commonTax = commonBase * 0.15,
        dayTax = dayBase * 0.2,
        commonDeducted = Math.min(commonCredit, commonTax),
        dayDeducted = Math.min(dayCredit, dayTax);
      commonCredit -= commonDeducted;
      dayCredit -= dayDeducted;
      const calculated = Math.max(
          0,
          commonTax + dayTax - commonDeducted - dayDeducted,
        ),
        carriedIn = taxCarry,
        available = taxCarry + calculated;
      const estimated = available >= 10 ? cents(available) : 0;
      taxCarry = estimated ? 0 : available;
      const pending = Math.max(0, estimated - d.paid);
      let status = d.review_count
        ? "Revisar exercício"
        : pending > 0
          ? "Pagamento pendente"
          : estimated > 0
            ? "Pago"
            : taxCarry > 0
              ? "Acumulado abaixo de R$ 10"
              : commonLoss + dayLoss > 0
                ? "Prejuízo a compensar"
                : "Sem imposto";
      const paymentMonth = shiftMonth(month, 1);
      let due = new Date(
        Date.UTC(
          Number(paymentMonth.slice(0, 4)),
          Number(paymentMonth.slice(5, 7)),
          0,
        ),
      );
      while ([0, 6].includes(due.getUTCDay()))
        due.setUTCDate(due.getUTCDate() - 1);
      rows.push({
        competence: month,
        ...d,
        common_loss_compensated: commonUsed,
        day_loss_compensated: dayUsed,
        common_taxable_base: commonBase,
        day_taxable_base: dayBase,
        common_loss_carry: commonLoss,
        day_loss_carry: dayLoss,
        common_irrf_carry: commonCredit,
        day_irrf_carry: dayCredit,
        irrf_deducted: commonDeducted + dayDeducted,
        tax_calculated: calculated,
        tax_carried_in: carriedIn,
        estimated_darf: estimated,
        tax_carry: taxCarry,
        pending: cents(pending),
        status,
        due_date: due.toISOString().slice(0, 10),
      });
    }
    return rows;
  }
  const api = {
    numeric,
    n,
    cents,
    today,
    dateValue,
    days,
    shiftMonth,
    probability,
    historicalVolatility,
    metrics,
    assess,
    rank,
    csv,
    coveredCalls,
    jade,
    roll,
    taxProjection,
  };
  root.FMDomain = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(globalThis);
