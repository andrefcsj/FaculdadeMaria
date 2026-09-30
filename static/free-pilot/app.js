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
          ? `<tr><td>${escape(x["Data fechamento"] || x.closed_at || "—")}</td><td>${escape(x.ativo || x.Ativo)}</td><td>${escape(x.tipo || x.Tipo)}</td><td>${escape(x.estrategia || x["Estratégia"])}</td><td>${money(x.Resultado_final || x.resultado_final || x.Lucro_tributavel)}</td><td><button data-reopen="${escape(x.closed_id)}">Reabrir</button></td></tr>`
          : `<tr><td>${escape(x.data_abertura)}</td><td>${escape(x.ativo)}</td><td>${escape(x.tipo)}</td><td>${escape(x.estrategia)}</td><td>${money(x.strike)}</td><td>${money(x.premio_opcao)}</td><td>${escape(x.vencimento)}</td>${target === "#open-operations" ? `<td><button data-close="${x.id}">Fechar</button><button data-remove="${x.id}">Excluir</button></td>` : ""}</tr>`,
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
    }[kind] || kind
  );
}
function renderExtra() {
  const cash = state.cash || [],
    credit = cash
      .filter((x) => ["aporte", "ajuste_credito"].includes(x.kind))
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
          `<tr><td>${escape(x.date)}</td><td>${escape(kindLabel(x.kind))}</td><td>${escape(x.description || "—")}</td><td class="${["aporte", "ajuste_credito"].includes(x.kind) ? "positive" : "negative"}">${money((["aporte", "ajuste_credito"].includes(x.kind) ? 1 : -1) * num(x.amount))}</td><td><button data-cash-delete="${escape(x.id)}">Excluir</button></td></tr>`,
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
  $("#settings-list").innerHTML = state.config
    .map(
      (x) =>
        `<label><strong>${escape(x.parametro)}</strong><input data-config="${escape(x.parametro)}" value="${escape(x.valor)}"></label>`,
    )
    .join("");
  const lots = state.equities || [], grouped = new Map();
  for (const lot of lots) {
    const asset = String(lot.asset || "").toUpperCase();
    if (!asset) continue;
    const item = grouped.get(asset) || { asset, quantity: 0, cost: 0, date: lot.acquisition_date || "" };
    item.quantity += num(lot.available_quantity ?? lot.quantity); item.cost += num(lot.cash_cost_total);
    if (!item.date || String(lot.acquisition_date) < item.date) item.date = lot.acquisition_date || item.date;
    grouped.set(asset, item);
  }
  const equities = [...grouped.values()].filter((item) => item.quantity > 0);
  $("#equity-quantity").textContent = String(equities.reduce((sum, item) => sum + item.quantity, 0));
  $("#equity-available").textContent = $("#equity-quantity").textContent;
  $("#equity-cost").textContent = money(equities.reduce((sum, item) => sum + item.cost, 0));
  $("#equity-rows").innerHTML = equities.map((item) => `<tr><td><strong>${escape(item.asset)}</strong></td><td>${item.quantity}</td><td>${money(item.cost / item.quantity)}</td><td>${money(item.cost)}</td><td>${escape(item.date || "—")}</td><td><button data-equity-edit="${escape(item.asset)}">Editar</button><button data-equity-sell="${escape(item.asset)}">Vender</button><button data-equity-delete="${escape(item.asset)}">Excluir</button></td></tr>`).join("") || "<tr><td colspan=6>Nenhuma ação registrada.</td></tr>";
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
    );
  $("#capital-total").textContent = money(cfg("Capital total inicial"));
  $("#capital-committed").textContent = money(capital);
  $("#premiums-open").textContent = money(premium);
  $("#roi-average").textContent =
    `${capital ? ((premium / capital) * 100).toFixed(2).replace(".", ",") : "0,00"}%`;
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
      (b.onclick = async () => {
        const value = prompt(
          "Resultado final da operação (positivo ou negativo):",
          "0",
        );
        if (value !== null && confirm("Fechar esta operação?")) {
          await request(`/operations/${b.dataset.close}/close`, {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({ resultado_final: value }),
          });
          await load();
        }
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
  document.querySelectorAll("[data-equity-delete]").forEach((b) => (b.onclick = async () => { if (confirm(`Excluir ${b.dataset.equityDelete} da carteira?`)) { await request(`/equities/${b.dataset.equityDelete}`, { method: "DELETE" }); await load(); } }));
  document.querySelectorAll("[data-equity-edit]").forEach((b) => (b.onclick = async () => { const current = (state.equities || []).filter((x) => x.asset === b.dataset.equityEdit); const quantity = prompt("Quantidade da posição:", String(current.reduce((sum, x) => sum + num(x.available_quantity ?? x.quantity), 0))); if (quantity === null) return; const cost = current.reduce((sum, x) => sum + num(x.cash_cost_total), 0); const average = prompt("Preço médio fiscal:", String(cost / Math.max(1, num(quantity)))); if (average === null) return; await request(`/equities/${b.dataset.equityEdit}`, { method: "PUT", headers: { "content-type": "application/json" }, body: JSON.stringify({ quantity, average_price: average, acquisition_date: current[0]?.acquisition_date }) }); await load(); }));
  document.querySelectorAll("[data-equity-sell]").forEach((b) => (b.onclick = async () => { const quantity = prompt(`Quantidade de ${b.dataset.equitySell} a vender:`); if (quantity === null) return; const sale_price = prompt("Preço de venda por ação:"); if (sale_price === null) return; await request(`/equities/${b.dataset.equitySell}/sell`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ quantity, sale_price }) }); await load(); }));
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
    equity: ["CARTEIRA DE AÇÕES", "Ações reconhecidas por exercício ou inclusão manual"],
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
$("#equity-form").onsubmit = async (e) => {
  e.preventDefault();
  try {
    await request("/equities", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(Object.fromEntries(new FormData(e.target))) });
    e.target.reset();
    e.target.elements.acquisition_date.value = new Date().toISOString().slice(0, 10);
    await load();
  } catch (err) { $("#message").textContent = err.message; }
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
$("#backup").onclick = async (e) => {
  e.preventDefault();
  const r = await request("/backup"),
    a = document.createElement("a");
  a.href = URL.createObjectURL(await r.blob());
  a.download = "faculdademaria-backup.json";
  a.click();
  URL.revokeObjectURL(a.href);
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
