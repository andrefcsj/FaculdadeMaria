const api = "api";
const $ = (selector) => document.querySelector(selector);
const message = (text, error = false) => { $("#message").textContent = text; $("#message").className = error ? "error" : ""; };

async function request(path, options = {}) {
  const response = await fetch(`${api}${path}`, { credentials: "same-origin", ...options });
  if (response.status === 401) { $("#app").hidden = true; $("#login").hidden = false; throw new Error("Sessão encerrada."); }
  if (!response.ok && response.status !== 204) throw new Error((await response.json().catch(() => ({}))).error || "Falha na operação.");
  return response;
}

function escape(value) { const item = document.createElement("span"); item.textContent = value ?? ""; return item.innerHTML; }
async function load() {
  const data = await (await request("/dashboard")).json();
  $("#open-count").textContent = data.operations.length;
  $("#closed-count").textContent = data.closed.length;
  $("#config-count").textContent = data.config.length;
  $("#operations").innerHTML = data.operations.map((row) => `<tr><td>${escape(row.data_abertura)}</td><td>${escape(row.ativo)}</td><td>${escape(row.tipo)}</td><td>${escape(row.estrategia)}</td><td>${escape(row.strike)}</td><td>${escape(row.premio_opcao)}</td><td><button data-id="${row.id}" class="remove">Excluir</button></td></tr>`).join("");
  document.querySelectorAll(".remove").forEach((button) => button.onclick = async () => { if (confirm("Excluir esta operação no piloto?")) { await request(`/operations/${button.dataset.id}`, { method: "DELETE" }); await load(); } });
}

$("#login-form").onsubmit = async (event) => { event.preventDefault(); try { await request("/session", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ pin: new FormData(event.target).get("pin") }) }); $("#login").hidden = true; $("#app").hidden = false; await load(); } catch { $("#login-error").textContent = "PIN inválido."; } };
$("#operation-form").onsubmit = async (event) => { event.preventDefault(); try { const item = Object.fromEntries(new FormData(event.target)); await request("/operations", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(item) }); event.target.reset(); message("Operação adicionada."); await load(); } catch (error) { message(error.message, true); } };
$("#backup").onclick = async () => { const response = await request("/backup"); const link = document.createElement("a"); link.href = URL.createObjectURL(await response.blob()); link.download = "faculdademaria-backup.json"; link.click(); URL.revokeObjectURL(link.href); };
$("#logout").onclick = async () => { await request("/session", { method: "DELETE" }); $("#app").hidden = true; $("#login").hidden = false; };
