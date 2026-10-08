(function (root) {
  "use strict";
  const D = root.FMDomain;
  function fields(line, delimiter = ";") {
    const row = [];
    let value = "",
      quoted = false;
    for (let i = 0; i <= line.length; i++) {
      const c = line[i] ?? delimiter;
      if (c === '"') {
        if (quoted && line[i + 1] === '"') {
          value += '"';
          i++;
        } else quoted = !quoted;
      } else if (c === delimiter && !quoted) {
        row.push(value);
        value = "";
      } else value += c;
    }
    return row;
  }
  function cvm(files, universe, year) {
    const wanted = new Set(universe.map((u) => u.cnpj));
    const accounts = Object.fromEntries(
      [...wanted].map((c) => [c, { current: {}, previous: {} }]),
    );
    for (const [name, bytes] of Object.entries(files)) {
      if (!/DRE_con|BPA_con|BPP_con|DFC_MI_con/.test(name)) continue;
      const text = new TextDecoder("iso-8859-1").decode(bytes),
        lines = text.split(/\r?\n/);
      const header = fields(lines.shift() || "");
      const index = Object.fromEntries(header.map((key, i) => [key, i]));
      for (const line of lines) {
        if (!line) continue;
        const row = fields(line),
          cnpj = row[index.CNPJ_CIA];
        if (!wanted.has(cnpj)) continue;
        const value = D.numeric(row[index.VL_CONTA]);
        if (value === null) continue;
        const period =
          row[index.ORDEM_EXERC] === "ÚLTIMO" ? "current" : "previous";
        accounts[cnpj][period][row[index.CD_CONTA]] = value;
      }
    }
    const get = (a, ...keys) => {
        for (const k of keys) if (a[k] !== undefined) return a[k];
        return null;
      },
      ratio = (v, low, high) =>
        Math.max(0, Math.min(1, (v - low) / (high - low)));
    return universe.map((u) => {
      const { current: c, previous: p } = accounts[u.cnpj] || {
        current: {},
        previous: {},
      };
      const positive = [],
        warnings = [];
      let quality = null,
        confidence = 0;
      if (u.model === "financial") {
        const profit = get(c, "3.11", "3.09"),
          prior = get(p, "3.11", "3.09"),
          equity = get(c, "2.08", "2.07", "2.03"),
          prevEquity = get(p, "2.08", "2.07", "2.03");
        confidence =
          [profit, prior, equity, prevEquity].filter((v) => v !== null).length /
          4;
        if (profit === null || equity === null || equity <= 0)
          warnings.push("Dados financeiros essenciais ausentes");
        else {
          quality = 0;
          if (profit > 0) {
            quality += 0.3;
            positive.push("Lucro líquido positivo");
          } else warnings.push("Prejuízo no último exercício");
          quality += ratio(profit / equity, 0, 0.2) * 0.3;
          if (prior > 0 && profit > 0) {
            quality += 0.2;
            positive.push("Lucro positivo em dois exercícios");
          }
          if (prevEquity > 0 && equity >= prevEquity) {
            quality += 0.2;
            positive.push("Patrimônio estável ou crescente");
          } else if (prevEquity !== null) warnings.push("Patrimônio recuou");
        }
      } else {
        const revenue = get(c, "3.01"),
          profit = get(c, "3.11"),
          prior = get(p, "3.11"),
          assets = get(c, "1"),
          equity = get(c, "2.03"),
          cfo = get(c, "6.01");
        confidence =
          [revenue, profit, prior, assets, equity, cfo].filter(
            (v) => v !== null,
          ).length / 6;
        if (
          profit === null ||
          assets === null ||
          equity === null ||
          equity <= 0
        )
          warnings.push("Dados fundamentais essenciais ausentes");
        else {
          quality = 0;
          if (profit > 0) {
            quality += 0.25;
            positive.push("Lucro líquido positivo");
          } else warnings.push("Prejuízo no último exercício");
          const roe = profit / equity;
          quality += ratio(roe, 0, 0.2) * 0.25;
          if (roe >= 0.12) positive.push("ROE consistente");
          else if (roe < 0.06) warnings.push("ROE baixo");
          if (cfo > 0) {
            quality += 0.2;
            positive.push("Geração operacional de caixa positiva");
          } else warnings.push("Caixa operacional ausente ou negativo");
          if (prior > 0 && profit > 0) {
            quality += 0.15;
            positive.push("Lucro positivo em dois exercícios");
          }
          quality += ratio(assets > 0 ? equity / assets : 0, 0.1, 0.5) * 0.15;
        }
      }
      return {
        ...u,
        quality_score: quality === null ? null : Math.min(1, quality),
        data_confidence: confidence,
        positive_notes: positive,
        warnings,
        source: `cvm_dfp_open_data:${u.model}`,
        reference_year: year,
        updated_at: new Date().toISOString(),
      };
    });
  }
  function cotahist(text, universe, asOf = D.today()) {
    const rootMap = new Map(universe.map((u) => [u.root, u.asset])),
      spots = new Map(),
      options = [];
    const iso = (s) => `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`;
    for (const line of text.split(/\r?\n/)) {
      if (line.length < 210 || line.slice(0, 2) !== "01") continue;
      const kind = line.slice(24, 27),
        symbol = line.slice(12, 24).trim(),
        premium = Number(line.slice(108, 121)) / 100;
      if (kind === "010") {
        spots.set(symbol, premium);
        continue;
      }
      if (!["070", "080"].includes(kind)) continue;
      const asset = rootMap.get(symbol.slice(0, 4));
      if (!asset) continue;
      const letter = symbol[4],
        type = "ABCDEFGHIJKL".includes(letter)
          ? "CALL"
          : "MNOPQRSTUVWX".includes(letter)
            ? "PUT"
            : null;
      if (!type) continue;
      options.push({
        asset,
        option_code: symbol,
        option_type: type,
        expiry: iso(line.slice(202, 210)),
        strike: Number(line.slice(188, 201)) / 100,
        premium,
        bid: Number(line.slice(121, 134)) / 100 || null,
        ask: Number(line.slice(134, 147)) / 100 || null,
        liquidity: Number(line.slice(152, 170)),
        timestamp: iso(line.slice(2, 10)),
        source: "b3_cotahist",
        data_confidence: 0.8,
      });
    }
    return options
      .map((o) => ({ ...o, spot_price: spots.get(o.asset) || null }))
      .filter((o) => D.metrics(o, { asOf }));
  }
  root.FMMarketData = { cvm, cotahist, fields };
  if (typeof module !== "undefined" && module.exports)
    module.exports = root.FMMarketData;
})(globalThis);
