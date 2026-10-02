const api = "api",
  $ = (s) => document.querySelector(s);
let state = { operations: [], config: [], closed: [] },
  sessionToken = sessionStorage.getItem("fm_session") || "";
const num = (v) => Number(String(v ?? 0).replace(",", ".")) || 0,
  money = (v) =>
    new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL",
    }).format(num(v)),
  escape = (v) => {
    const n = document.createElement("span");
    n.textContent = v ?? "";
    return n.innerHTML;
  };
async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (sessionToken) headers.set("Authorization", `Bearer ${sessionToken}`);
  const r = await fetch(`${api}${path}`, {
    credentials: "same-origin",
    ...options,
    headers,
  });
  if (r.status === 401) {
    sessionStorage.removeItem("fm_session");
    sessionToken = "";
    $("#app").hidden = true;
    $("#login").hidden = false;
    throw Error("Sessão encerrada");
  }
  if (!r.ok && r.status !== 204)
    throw Error(
      (await r.json().catch(() => ({}))).error || "Falha na operação",
    );
  return r;
}
const cfg = (name, fallback = 0) =>
    num(state.config.find((x) => x.parametro === name)?.valor ?? fallback),
  opened = () =>
    state.operations.filter((x) => String(x.status).toLowerCase() === "aberta");
function rows(target, list, closed = false) {
  $(target).innerHTML =
    list
      .map((x) =>
        closed
          ? `<tr><td>${escape(x["Data fechamento"] || x.closed_at || "—")}</td><td>${escape(x.ativo || x.Ativo)}</td><td>${escape(x.tipo || x.Tipo)}</td><td>${escape(x.estrategia || x["Estratégia"])}</td><td>${money(x.premio_opcao || x.Premio_liquido)}</td><td class="${num(x.Resultado_final || x.resultado_final || x.Lucro_tributavel) < 0 ? "negative" : "positive"}">${money(x.Resultado_final || x.resultado_final || x.Lucro_tributavel)}</td><td>${escape(x.Observacoes || x.observacoes || "—")}</td><td><button data-reopen="${escape(x.closed_id)}">Reabrir</button></td></tr>`
          : `<tr><td>${escape(x.data_abertura)}</td><td>${escape(x.ativo)}</td><td>${escape(x.tipo)}</td><td>${escape(x.estrategia)}</td><td>${money(x.strike)}</td><td>${money(x.premio_opcao)}</td><td>${escape(x.vencimento)}</td>${target === "#open-operations" ? `<td><button data-edit="${x.id}">Editar</button><button data-close="${x.id}">Fechar</button><button data-remove="${x.id}">Excluir</button></td>` : ""}</tr>`,
      )
      .join("") || "<tr><td colspan=8>Nenhum registro.</td></tr>";
}
function kindLabel(kind) {
  return (
    {
      aporte: "Aporte",
      retirada: "Retirada",
      ajuste_credito: "Crédito manual",
      ajuste_debito: "Débito manual",
      venda_acoes: "Venda de ações",
    }[kind] || kind
  );
}
function renderExtra() {
  const cash = state.cash || [],
    credit = cash
      .filter((x) =>
        ["aporte", "ajuste_credito", "venda_acoes"].includes(x.kind),
      )
      .reduce((s, x) => s + num(x.amount), 0),
    debit = cash
      .filter((x) => ["retirada", "ajuste_debito"].includes(x.kind))
      .reduce((s, x) => s + num(x.amount), 0);
  $("#cash-balance").textContent = money(credit - debit);
  $("#cash-contributions").textContent = money(credit);
  $("#cash-withdrawals").textContent = money(debit);
  $("#cash-rows").innerHTML =
    cash
      .map(
        (x) =>
          `<tr><td>${escape(x.date)}</td><td>${escape(kindLabel(x.kind))}</td><td>${escape(x.description || "—")}</td><td class="${["aporte", "ajuste_credito", "venda_acoes"].includes(x.kind) ? "positive" : "negative"}">${money((["aporte", "ajuste_credito", "venda_acoes"].includes(x.kind) ? 1 : -1) * num(x.amount))}</td><td><button data-cash-delete="${escape(x.id)}">Excluir</button></td></tr>`,
      )
      .join("") || "<tr><td colspan=5>Nenhuma movimentação.</td></tr>";
  $("#notes-rows").innerHTML =
    (state.notes || [])
      .map(
        (x) =>
          `<tr><td>${escape(x.trade_date || "—")}</td><td>${escape(x.note_number || "—")}</td><td>${escape(x.trade?.option_code || "—")}</td><td>${money((String(x.cash_direction || "C").toUpperCase() === "C" ? 1 : -1) * num(x.net_cash))}</td><td>${money(x.operational_costs)}</td></tr>`,
      )
      .join("") ||
    "<tr><td colspan=5>Nenhuma nota estruturada no piloto.</td></tr>";
  const result = (state.closed || []).reduce(
      (s, x) =>
        s + num(x.Resultado_final || x.resultado_final || x.Lucro_tributavel),
      0,
    ),
    tax = result * Math.max(0, cfg("Aliquota IR opcoes", 0.15));
  $("#tax-result").textContent = money(result);
  $("#tax-estimate").textContent = money(tax);
  $("#tax-paid").textContent = money(
    (state.darfs || []).reduce((s, x) => s + num(x.amount), 0),
  );
  $("#darf-rows").innerHTML =
    (state.darfs || [])
      .map(
        (x) =>
          `<tr><td>${escape(x.competence)}</td><td>${escape(x.payment_date)}</td><td>${money(x.amount)}</td><td>${escape(x.description || "—")}</td><td><button data-darf-delete="${escape(x.id)}">Excluir</button></td></tr>`,
      )
      .join("") || "<tr><td colspan=5>Nenhuma DARF registrada.</td></tr>";
  const taxMonths = new Map();
  (state.closed || []).forEach((item) => {
    const competence = String(item["Data fechamento"] || item.closed_at || "").slice(0, 7);
    if (!/^\d{4}-\d{2}$/.test(competence)) return;
    const row = taxMonths.get(competence) || { competence, result: 0, paid: 0 };
    row.result += num(item.Resultado_final || item.resultado_final || item.Lucro_tributavel);
    taxMonths.set(competence, row);
  });
  (state.darfs || []).forEach((item) => {
    const competence = String(item.competence || "");
    if (!/^\d{4}-\d{2}$/.test(competence)) return;
    const row = taxMonths.get(competence) || { competence, result: 0, paid: 0 };
    row.paid += num(item.amount);
    taxMonths.set(competence, row);
  });
  const rate = Math.max(0, cfg("Aliquota IR opcoes", 0.15));
  $("#tax-month-rows").innerHTML = [...taxMonths.values()]
    .sort((a, b) => b.competence.localeCompare(a.competence))
    .map((row) => {
      const estimated = Math.max(0, row.result) * rate,
        balance = estimated - row.paid;
      return `<tr><td><strong>${escape(row.competence)}</strong></td><td class="${row.result < 0 ? "negative" : "positive"}">${money(row.result)}</td><td>${money(estimated)}</td><td>${money(row.paid)}</td><td class="${balance > 0 ? "negative" : "positive"}">${money(balance)}</td></tr>`;
    })
    .join("") || "<tr><td colspan=5>Nenhuma competência registrada.</td></tr>";
  $("#settings-list").innerHTML = state.config
    .map(
      (x) =>
        `<label><strong>${escape(x.parametro)}</strong><input data-config="${escape(x.parametro)}" value="${escape(x.valor)}"></label>`,
    )
    .join("");
  const lots = state.equities || [],
    grouped = new Map();
  for (const lot of lots) {
    const asset = String(lot.asset || "").toUpperCase();
    if (!asset) continue;
    const item = grouped.get(asset) || {
      asset,
      quantity: 0,
      cost: 0,
      date: lot.acquisition_date || "",
    };
    item.quantity += num(lot.available_quantity ?? lot.quantity);
    item.cost += num(lot.cash_cost_total);
    if (!item.date || String(lot.acquisition_date) < item.date)
      item.date = lot.acquisition_date || item.date;
    grouped.set(asset, item);
  }
  const equities = [...grouped.values()].filter((item) => item.quantity > 0);
  $("#equity-quantity").textContent = String(
    equities.reduce((sum, item) => sum + item.quantity, 0),
  );
  $("#equity-available").textContent = $("#equity-quantity").textContent;
  $("#equity-cost").textContent = money(
    equities.reduce((sum, item) => sum + item.cost, 0),
  );
  $("#equity-rows").innerHTML =
    equities
      .map(
        (item) =>
          `<tr><td><strong>${escape(item.asset)}</strong></td><td>${item.quantity}</td><td>${money(item.cost / item.quantity)}</td><td>${money(item.cost)}</td><td>${escape(item.date || "—")}</td><td><button data-equity-edit="${escape(item.asset)}">Editar</button><button data-equity-sell="${escape(item.asset)}">Vender</button><button data-equity-delete="${escape(item.asset)}">Excluir</button></td></tr>`,
      )
      .join("") || "<tr><td colspan=6>Nenhuma ação registrada.</td></tr>";
  const monthly = new Map(),
    addPremium = (date, premium, closedResult = 0) => {
      const month = String(date || "").slice(0, 7) || "Sem data";
      const row = monthly.get(month) || {
        month,
        count: 0,
        premium: 0,
        result: 0,
      };
      row.count += 1;
      row.premium += num(premium);
      row.result += num(closedResult);
      monthly.set(month, row);
    };
  state.operations.forEach((item) =>
    addPremium(
      item.data_abertura,
      num(item.premio_opcao) *
        num(item.contratos) *
        cfg("Tamanho contrato opcoes", 100) -
        num(item.custos) -
        num(item.irrf),
    ),
  );
  (state.closed || []).forEach((item) =>
    addPremium(
      item["Data fechamento"] || item.closed_at,
      item.Premio_liquido || item.premio_opcao,
      item.Resultado_final || item.resultado_final,
    ),
  );
  const premiumRows = [...monthly.values()].sort((a, b) =>
    a.month.localeCompare(b.month),
  );
  const received = premiumRows.reduce((sum, row) => sum + row.premium, 0),
    closedResult = premiumRows.reduce((sum, row) => sum + row.result, 0),
    costs = state.operations.reduce(
      (sum, item) => sum + num(item.custos) + num(item.irrf),
      0,
    );
  $("#premium-total").textContent = money(received);
  $("#premium-costs").textContent = money(costs);
  $("#premium-retained").textContent = money(received + closedResult - costs);
  $("#premium-rows").innerHTML =
    premiumRows
      .slice()
      .reverse()
      .map(
        (row) =>
          `<tr><td>${escape(row.month)}</td><td>${row.count}</td><td>${money(row.premium)}</td><td>${money(row.result)}</td></tr>`,
      )
      .join("") || "<tr><td colspan=4>Nenhum prêmio registrado.</td></tr>";
  const top = Math.max(...premiumRows.map((row) => Math.abs(row.premium)), 1);
  $("#premium-chart").innerHTML =
    premiumRows
      .map(
        (row) =>
          `<div><i style="height:${Math.max(5, (Math.abs(row.premium) / top) * 130)}px"></i><strong>${money(row.premium)}</strong><small>${escape(row.month)}</small></div>`,
      )
    .join("") || "Sem dados para o gráfico.";
  const quotes = new Map(
    (state.manual_option_quotes || []).map((quote) => [
      String(quote.option_code).toUpperCase(),
      quote,
    ]),
  );
  $("#radar-operations").innerHTML = opened()
    .map((operation) => {
      const quote = quotes.get(String(operation.ativo).toUpperCase());
      const opening = num(operation.premio_opcao);
      const current = quote ? num(quote.price) : null;
      const estimated = current === null ? null : (opening - current) * num(operation.contratos) * cfg("Tamanho contrato opcoes", 100);
      return `<tr><td><strong>${escape(operation.ativo)}</strong></td><td>${money(opening)}</td><td>${current === null ? "Sem cotação" : money(current)}</td><td class="${estimated === null ? "" : estimated >= 0 ? "positive" : "negative"}">${estimated === null ? "—" : money(estimated)}</td></tr>`;
    })
    .join("") || "<tr><td colspan=4>Nenhuma posição aberta para monitorar.</td></tr>";
  $("#quote-rows").innerHTML = (state.manual_option_quotes || [])
    .map(
      (quote) =>
        `<tr><td><strong>${escape(quote.option_code)}</strong></td><td>${money(quote.price)}</td><td>${escape(String(quote.quoted_at).replace("T", " "))}</td><td><button data-quote-delete="${escape(quote.option_code)}">Excluir</button></td></tr>`,
    )
    .join("") || "<tr><td colspan=4>Nenhuma cotação manual registrada.</td></tr>";
}
function render() {
  const open = opened(),
    size = cfg("Tamanho contrato opcoes", 100),
    capital = open.reduce(
      (s, x) => s + num(x.contratos) * num(x.strike) * size,
      0,
    ),
    premium = open.reduce(
      (s, x) => s + num(x.contratos) * num(x.premio_opcao) * size,
      0,
    ),
    cash = (state.cash || []).reduce(
      (sum, item) =>
        sum +
        (["aporte", "ajuste_credito", "venda_acoes"].includes(item.kind)
          ? num(item.amount)
          : -num(item.amount)),
      0,
    ),
    equityCost = (state.equities || []).reduce(
      (sum, item) => sum + num(item.cash_cost_total),
      0,
    ),
    patrimony = cfg("Capital total inicial") + cash,
    available = patrimony - capital - equityCost,
    monthKey = new Date().toISOString().slice(0, 7),
    monthlyPremium = [...(state.operations || []), ...(state.closed || [])]
      .filter((item) => String(item.data_abertura || item.data_fechamento || "").slice(0, 7) === monthKey)
      .reduce(
        (sum, item) =>
          sum +
          num(item.contratos) *
            num(item.premio_opcao ?? item.Premio_liquido) *
            size,
        0,
      );
  $("#capital-total").textContent = money(patrimony);
  $("#available-to-trade").textContent = money(available);
  $("#capital-committed").textContent = money(capital);
  $("#premiums-open").textContent = money(premium);
  $("#premiums-month").textContent = money(monthlyPremium);
  $("#month-reference").textContent = new Intl.DateTimeFormat("pt-BR", {
    month: "long",
    year: "numeric",
  }).format(new Date());
  $("#roi-average").textContent =
    `${capital ? ((premium / capital) * 100).toFixed(2).replace(".", ",") : "0,00"}%`;
  const closedRows = state.closed || [];
  const resultOf = (item) =>
    num(item.Resultado_final || item.resultado_final || item.Lucro_tributavel);
  const best = closedRows.length
    ? closedRows.reduce((current, item) => (resultOf(item) > resultOf(current) ? item : current))
    : null;
  const worst = closedRows.length
    ? closedRows.reduce((current, item) => (resultOf(item) < resultOf(current) ? item : current))
    : null;
  $("#closed-count").textContent = String(closedRows.length);
  $("#closed-total").textContent = money(closedRows.reduce((sum, item) => sum + resultOf(item), 0));
  $("#closed-best").textContent = money(best ? resultOf(best) : 0);
  $("#closed-worst").textContent = money(worst ? resultOf(worst) : 0);
  $("#closed-best-label").textContent = best ? String(best.ativo || best.Ativo || "—") : "Sem histórico";
  $("#closed-worst-label").textContent = worst ? String(worst.ativo || worst.Ativo || "—") : "Sem histórico";
  const insightTitle = open.length
    ? `${open.length} operação${open.length === 1 ? "" : "ões"} aberta${open.length === 1 ? "" : "s"} para acompanhar`
    : "Nenhuma operação aberta no momento";
  $("#dashboard-insight-title").textContent = insightTitle;
  $("#dashboard-insight").textContent = open.length
    ? `Há ${money(capital)} em garantias e ${money(premium)} em prêmios brutos nas posições abertas. Saldo estimado para novas operações: ${money(available)}.`
    : `O piloto está sem posições abertas. O saldo estimado para operar é ${money(available)}.`;
  const rollSelect = $("#roll-operation");
  const selectedRoll = rollSelect.value;
  rollSelect.innerHTML =
    '<option value="">Selecione uma PUT aberta</option>' +
    open
      .filter((item) => String(item.tipo).toUpperCase() === "PUT")
      .map(
        (item) =>
          `<option value="${escape(item.id)}">${escape(item.ativo)} · strike ${money(item.strike)} · vence ${escape(item.vencimento)}</option>`,
      )
      .join("");
  if ([...rollSelect.options].some((option) => option.value === selectedRoll))
    rollSelect.value = selectedRoll;
  rows("#dashboard-operations", open);
  rows("#open-operations", open);
  rows("#closed-operations", state.closed, true);
  $("#expiries").innerHTML =
    open
      .map(
        (x) =>
          `<div><span class=expiry-day>${Math.max(0, Math.ceil((new Date(`${x.vencimento}T00:00:00`) - new Date()) / 86400000))}<small> dias</small></span><p><strong>${escape(x.ativo)}</strong><small>${escape(x.vencimento)}</small></p></div>`,
      )
      .join("") || "Agenda livre";
  renderExtra();
  document.querySelectorAll("[data-remove]").forEach(
    (b) =>
      (b.onclick = async () => {
        if (confirm("Excluir esta operação no piloto?")) {
          await request(`/operations/${b.dataset.remove}`, {
            method: "DELETE",
          });
          await load();
        }
      }),
  );
  document.querySelectorAll("[data-close]").forEach(
    (b) =>
      (b.onclick = () => {
        const operation = state.operations.find(
          (item) => String(item.id) === String(b.dataset.close),
        );
        if (!operation) return;
        const form = $("#close-operation-form");
        form.reset();
        form.elements.operation_id.value = operation.id;
        form.elements.data_fechamento.value = new Date().toISOString().slice(0, 10);
        $("#close-operation-title").textContent = `Fechar ${operation.ativo} · ${operation.tipo}`;
        $("#close-operation-dialog").showModal();
      }),
  );
  document.querySelectorAll("[data-edit]").forEach(
    (button) =>
      (button.onclick = () => {
        const operation = state.operations.find(
          (item) => String(item.id) === String(button.dataset.edit),
        );
        if (!operation) return;
        const form = $("#edit-operation-form");
        for (const [name, value] of Object.entries(operation)) {
          const field = form.elements[name];
          if (field) field.value = value ?? "";
        }
        form.elements.id.value = operation.id;
        $("#edit-operation-dialog").showModal();
      }),
  );
  document.querySelectorAll("[data-reopen]").forEach(
    (b) =>
      (b.onclick = async () => {
        if (confirm("Reabrir esta operação?")) {
          await request(`/closed/${b.dataset.reopen}/reopen`, {
            method: "POST",
          });
          await load();
        }
      }),
  );
  document.querySelectorAll("[data-cash-delete]").forEach(
    (b) =>
      (b.onclick = async () => {
        if (confirm("Excluir esta movimentação?")) {
          await request(`/cash/${b.dataset.cashDelete}`, { method: "DELETE" });
          await load();
        }
      }),
  );
  document.querySelectorAll("[data-darf-delete]").forEach(
    (b) =>
      (b.onclick = async () => {
        if (confirm("Excluir esta DARF?")) {
          await request(`/darfs/${b.dataset.darfDelete}`, { method: "DELETE" });
          await load();
        }
      }),
  );
  document.querySelectorAll("[data-equity-delete]").forEach(
    (b) =>
      (b.onclick = async () => {
        if (confirm(`Excluir ${b.dataset.equityDelete} da carteira?`)) {
          await request(`/equities/${b.dataset.equityDelete}`, {
            method: "DELETE",
          });
          await load();
        }
      }),
  );
  document.querySelectorAll("[data-equity-edit]").forEach(
    (b) =>
      (b.onclick = async () => {
        const current = (state.equities || []).filter(
          (x) => x.asset === b.dataset.equityEdit,
        );
        const quantity = prompt(
          "Quantidade da posição:",
          String(
            current.reduce(
              (sum, x) => sum + num(x.available_quantity ?? x.quantity),
              0,
            ),
          ),
        );
        if (quantity === null) return;
        const cost = current.reduce(
          (sum, x) => sum + num(x.cash_cost_total),
          0,
        );
        const average = prompt(
          "Preço médio fiscal:",
          String(cost / Math.max(1, num(quantity))),
        );
        if (average === null) return;
        await request(`/equities/${b.dataset.equityEdit}`, {
          method: "PUT",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            quantity,
            average_price: average,
            acquisition_date: current[0]?.acquisition_date,
          }),
        });
        await load();
      }),
  );
  document.querySelectorAll("[data-equity-sell]").forEach(
    (b) =>
      (b.onclick = async () => {
        const quantity = prompt(
          `Quantidade de ${b.dataset.equitySell} a vender:`,
        );
        if (quantity === null) return;
        const sale_price = prompt("Preço de venda por ação:");
        if (sale_price === null) return;
        await request(`/equities/${b.dataset.equitySell}/sell`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ quantity, sale_price }),
        });
        await load();
      }),
  );
  document.querySelectorAll("[data-quote-delete]").forEach(
    (button) =>
      (button.onclick = async () => {
        if (confirm(`Excluir a cotação de ${button.dataset.quoteDelete}?`)) {
          await request(`/quotes/${button.dataset.quoteDelete}`, { method: "DELETE" });
          await load();
        }
      }),
  );
}
async function load() {
  state = await (await request("/dashboard")).json();
  render();
  $("#last-updated").textContent = new Date().toLocaleString("pt-BR");
}
function screen(name) {
  document.querySelectorAll(".screen").forEach((x) => (x.hidden = true));
  $(`#${name}-screen`).hidden = false;
  document
    .querySelectorAll("[data-screen]")
    .forEach((x) => x.classList.toggle("active", x.dataset.screen === name));
  const labels = {
    dashboard: ["DASHBOARD EXECUTIVO", "Visão geral da sua carteira de opções"],
    open: ["OPERAÇÕES ABERTAS", "Posições ativas e gerenciamento"],
    closed: ["OPERAÇÕES FECHADAS", "Histórico de resultados"],
    premiums: [
      "PRÊMIOS RECEBIDOS",
      "Histórico de créditos e resultado por ciclo",
    ],
    simulators: ["SIMULADORES", "ROI e payoff de opções no vencimento"],
    radar: ["RADAR DE POSIÇÕES", "Acompanhamento manual e gratuito das suas opções abertas"],
    equity: [
      "CARTEIRA DE AÇÕES",
      "Ações reconhecidas por exercício ou inclusão manual",
    ],
    cash: ["APORTES REALIZADOS", "Livro-caixa e evolução do saldo"],
    notes: ["NOTAS IMPORTADAS", "Créditos, custos e acompanhamento das notas"],
    tax: ["APURAÇÃO DE IR", "Memória gerencial de renda variável"],
    settings: ["CONFIGURAÇÕES", "Parâmetros do sistema"],
    notice: [
      "MIGRAÇÃO EM ANDAMENTO",
      "Esta tela será preservada no Cloudflare Free",
    ],
  };
  $("#page-title").textContent = labels[name][0];
  $("#page-subtitle").textContent = labels[name][1];
}
async function restore() {
  await load();
  const today = new Date().toISOString().slice(0, 10),
    month = today.slice(0, 7),
    now = new Date().toISOString().slice(0, 16);
  const defaults = [
    ["#operation-form [name=data_abertura]", today],
    ["#equity-form [name=acquisition_date]", today],
    ["#cash-form [name=date]", today],
    ["#darf-form [name=payment_date]", today],
    ["#darf-form [name=competence]", month],
    ["#quote-form [name=quoted_at]", now],
  ];
  defaults.forEach(([selector, value]) => {
    const field = $(selector);
    if (!field.value) field.value = value;
  });
  $("#login").hidden = true;
  $("#app").hidden = false;
  window.scrollTo(0, 0);
}
async function signIn(pin) {
  const r = await request("/session", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ pin }),
    }),
    data = await r.json();
  sessionToken = data.token;
  sessionStorage.setItem("fm_session", sessionToken);
  await restore();
}
$("#login-form").onsubmit = async (e) => {
  e.preventDefault();
  const button = e.target.querySelector("button");
  button.disabled = true;
  button.textContent = "Entrando…";
  $("#login-error").textContent = "";
  try {
    await signIn(new FormData(e.target).get("pin"));
  } catch (err) {
    $("#login-error").textContent =
      err.message === "Sessão encerrada"
        ? "PIN inválido. Confira e tente novamente."
        : "Não foi possível carregar o sistema. Tente novamente.";
  } finally {
    button.disabled = false;
    button.textContent = "Entrar no sistema";
  }
};
document.querySelectorAll("[data-screen]").forEach(
  (a) =>
    (a.onclick = (e) => {
      e.preventDefault();
      screen(a.dataset.screen);
    }),
);
$("#operation-form").onsubmit = async (e) => {
  e.preventDefault();
  try {
    await request("/operations", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(Object.fromEntries(new FormData(e.target))),
    });
    e.target.reset();
    await load();
  } catch (err) {
    $("#message").textContent = err.message;
  }
};
document
  .querySelectorAll("[data-close-edit]")
  .forEach(
    (button) => (button.onclick = () => $("#edit-operation-dialog").close()),
  );
document
  .querySelectorAll("[data-close-operation]")
  .forEach(
    (button) =>
      (button.onclick = () => $("#close-operation-dialog").close()),
  );
$("#edit-operation-form").onsubmit = async (e) => {
  e.preventDefault();
  const form = e.target,
    id = form.elements.id.value;
  try {
    const data = Object.fromEntries(new FormData(form));
    delete data.id;
    await request(`/operations/${id}`, {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(data),
    });
    $("#edit-operation-dialog").close();
    await load();
  } catch (err) {
    $("#message").textContent = err.message;
  }
};
$("#close-operation-form").onsubmit = async (e) => {
  e.preventDefault();
  const form = e.target,
    id = form.elements.operation_id.value;
  try {
    const data = Object.fromEntries(new FormData(form));
    delete data.operation_id;
    await request(`/operations/${id}/close`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(data),
    });
    $("#close-operation-dialog").close();
    await load();
  } catch (err) {
    $("#message").textContent = err.message;
  }
};
$("#equity-form").onsubmit = async (e) => {
  e.preventDefault();
  try {
    await request("/equities", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(Object.fromEntries(new FormData(e.target))),
    });
    e.target.reset();
    e.target.elements.acquisition_date.value = new Date()
      .toISOString()
      .slice(0, 10);
    await load();
  } catch (err) {
    $("#message").textContent = err.message;
  }
};
$("#cash-form").onsubmit = async (e) => {
  e.preventDefault();
  try {
    await request("/cash", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(Object.fromEntries(new FormData(e.target))),
    });
    e.target.reset();
    e.target.elements.date.value = new Date().toISOString().slice(0, 10);
    await load();
  } catch (err) {
    $("#message").textContent = err.message;
  }
};
$("#darf-form").onsubmit = async (e) => {
  e.preventDefault();
  try {
    await request("/darfs", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(Object.fromEntries(new FormData(e.target))),
    });
    e.target.reset();
    await load();
  } catch (err) {
    $("#message").textContent = err.message;
  }
};
$("#roi-form").onsubmit = (e) => {
  e.preventDefault();
  const data = Object.fromEntries(new FormData(e.target)),
    size = cfg("Tamanho contrato opcoes", 100),
    capital = num(data.strike) * num(data.contracts) * size,
    credit = num(data.premium) * num(data.contracts) * size,
    roi = capital ? (credit / capital) * 100 : 0,
    monthly = num(data.days) ? (roi / num(data.days)) * 30 : 0;
  $("#roi-result").innerHTML =
    `<strong>${money(credit)} de prêmio bruto</strong><span>Capital necessário: ${money(capital)} · ROI do ciclo: ${roi.toFixed(2).replace(".", ",")}% · Equivalente mensal: ${monthly.toFixed(2).replace(".", ",")}%</span>`;
};
$("#payoff-form").onsubmit = (e) => {
  e.preventDefault();
  const data = Object.fromEntries(new FormData(e.target)),
    size = cfg("Tamanho contrato opcoes", 100),
    contracts = num(data.contracts),
    strike = num(data.strike),
    premium = num(data.premium),
    price = num(data.price),
    intrinsic =
      data.type === "PUT"
        ? Math.max(strike - price, 0)
        : Math.max(price - strike, 0),
    result = (premium - intrinsic) * contracts * size,
    breakEven = data.type === "PUT" ? strike - premium : strike + premium;
  $("#payoff-result").innerHTML =
    `<strong class="${result >= 0 ? "positive" : "negative"}">${money(result)} no vencimento</strong><span>Valor intrínseco: ${money(intrinsic)} por ação · Ponto de equilíbrio: ${money(breakEven)} · ${data.type} vendida com ${contracts} contrato(s).</span>`;
};
$("#quote-form").onsubmit = async (e) => {
  e.preventDefault();
  try {
    await request("/quotes", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(Object.fromEntries(new FormData(e.target))),
    });
    e.target.reset();
    e.target.elements.quoted_at.value = new Date().toISOString().slice(0, 16);
    await load();
  } catch (err) {
    $("#message").textContent = err.message;
  }
};
$("#roll-form").onsubmit = (e) => {
  e.preventDefault();
  const data = Object.fromEntries(new FormData(e.target)),
    operation = opened().find((item) => String(item.id) === data.operation_id),
    size = cfg("Tamanho contrato opcoes", 100);
  if (!operation) {
    $("#roll-result").textContent = "Selecione uma PUT aberta válida.";
    return;
  }
  const contracts = num(operation.contratos),
    originalPremium = num(operation.premio_opcao),
    buyback = num(data.buyback),
    newPremium = num(data.new_premium),
    newStrike = num(data.new_strike),
    netCredit = (newPremium - buyback) * contracts * size,
    accumulatedCredit = (originalPremium - buyback + newPremium) * contracts * size,
    newGuarantee = newStrike * contracts * size,
    originalStrike = num(operation.strike);
  $("#roll-result").innerHTML =
    `<strong class="${netCredit >= 0 ? "positive" : "negative"}">${money(netCredit)} de crédito líquido na rolagem</strong><span>PUT atual: ${escape(operation.ativo)} a ${money(originalStrike)} · Nova garantia: ${money(newGuarantee)} · Crédito acumulado das duas etapas: ${money(accumulatedCredit)} · Novo vencimento: ${escape(data.new_expiry)}.</span>`;
};
$("#save-config").onclick = async () => {
  try {
    const values = [...document.querySelectorAll("[data-config]")].map(
      (input) => ({ parametro: input.dataset.config, valor: input.value }),
    );
    await request("/config", {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ values }),
    });
    await load();
    $("#message").textContent = "Configurações salvas.";
  } catch (err) {
    $("#message").textContent = err.message;
  }
};
async function downloadBackup() {
  const r = await request("/backup"),
    a = document.createElement("a");
  a.href = URL.createObjectURL(await r.blob());
  a.download = "faculdademaria-backup.json";
  a.click();
  URL.revokeObjectURL(a.href);
}
$("#backup").onclick = async (e) => {
  e.preventDefault();
  await downloadBackup();
};
$("#backup-settings").onclick = downloadBackup;
$("#restore-form").onsubmit = async (e) => {
  e.preventDefault();
  const file = e.target.elements.backup_file.files[0];
  if (!file) return;
  if (!confirm("Restaurar este backup substituirá os dados atuais apenas no piloto do Cloudflare. Deseja continuar?"))
    return;
  try {
    const backup = JSON.parse(await file.text());
    const response = await request("/restore", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(backup),
    });
    const result = await response.json();
    await load();
    e.target.reset();
    $("#message").textContent = `${result.restored} registro(s) restaurado(s) no piloto.`;
  } catch (err) {
    $("#message").textContent =
      err instanceof SyntaxError
        ? "O arquivo selecionado não é um JSON de backup válido."
        : err.message;
  }
};
$("#logout").onclick = async () => {
  await request("/session", { method: "DELETE" });
  sessionStorage.removeItem("fm_session");
  sessionToken = "";
  $("#app").hidden = true;
  $("#login").hidden = false;
};
const magic = new URLSearchParams(location.hash.slice(1)).get("pin");
if (magic) {
  history.replaceState(null, "", location.pathname + location.search);
  signIn(magic).catch(() => {
    $("#login-error").textContent = "Não foi possível entrar automaticamente.";
  });
} else
  restore().catch((err) => {
    if (sessionToken)
      $("#login-error").textContent =
        "Não foi possível carregar os dados. Tente entrar novamente.";
  });
