/* Move every app popup by its header, using mouse, touch or pen. */
(() => {
  const popups = new Map();
  const properties = [
    "position",
    "inset",
    "left",
    "top",
    "right",
    "bottom",
    "margin",
    "width",
    "transform",
  ];
  function reset(popup) {
    const entry = popups.get(popup);
    if (!entry) return;
    for (const [property, original] of entry.original) {
      if (original.value)
        popup.style.setProperty(property, original.value, original.priority);
      else popup.style.removeProperty(property);
    }
    popup.classList.remove("fm-popup-moving");
    entry.drag = null;
  }
  function attach(popup) {
    if (popups.has(popup)) return;
    const header = popup.querySelector("header");
    if (!header) return;
    const entry = {
      original: properties.map((property) => [
        property,
        {
          value: popup.style.getPropertyValue(property),
          priority: popup.style.getPropertyPriority(property),
        },
      ]),
      drag: null,
    };
    popups.set(popup, entry);
    header.classList.add("fm-popup-handle");
    header.title =
      "Arraste para mover a janela. Clique duas vezes no cabeçalho para centralizar.";
    const interactive = (target) =>
      target.closest(
        'button, input, select, textarea, a, label, [contenteditable="true"]',
      );
    header.addEventListener("pointerdown", (event) => {
      if (event.button !== 0 || interactive(event.target)) return;
      const rect = popup.getBoundingClientRect();
      entry.drag = {
        pointer: event.pointerId,
        x: event.clientX,
        y: event.clientY,
        left: rect.left,
        top: rect.top,
      };
      Object.assign(popup.style, {
        position: "fixed",
        inset: "auto",
        margin: "0",
        left: `${rect.left}px`,
        top: `${rect.top}px`,
        width: `${rect.width}px`,
        transform: "none",
      });
      popup.classList.add("fm-popup-moving");
      header.setPointerCapture(event.pointerId);
      event.preventDefault();
    });
    header.addEventListener("pointermove", (event) => {
      const drag = entry.drag;
      if (!drag || drag.pointer !== event.pointerId) return;
      const rect = popup.getBoundingClientRect();
      const visible = Math.min(120, rect.width);
      const left = Math.max(
        -rect.width + visible,
        Math.min(innerWidth - visible, drag.left + event.clientX - drag.x),
      );
      const top = Math.max(
        0,
        Math.min(
          innerHeight - Math.min(64, header.getBoundingClientRect().height),
          drag.top + event.clientY - drag.y,
        ),
      );
      popup.style.left = `${left}px`;
      popup.style.top = `${top}px`;
    });
    const release = (event) => {
      if (entry.drag?.pointer !== event.pointerId) return;
      entry.drag = null;
      popup.classList.remove("fm-popup-moving");
      if (header.hasPointerCapture(event.pointerId))
        header.releasePointerCapture(event.pointerId);
    };
    header.addEventListener("pointerup", release);
    header.addEventListener("pointercancel", release);
    header.addEventListener("lostpointercapture", release);
    header.addEventListener("dblclick", (event) => {
      if (!interactive(event.target)) reset(popup);
    });
    popup.addEventListener("close", () => reset(popup));
  }
  // Native browser confirm/prompt windows cannot move across the page.
  // Keep their existing decisions in one movable, accessible app dialog.
  const question = document.createElement("dialog");
  question.id = "system-question-dialog";
  question.className = "free-dialog fm-system-question";
  question.setAttribute("aria-labelledby", "system-question-title");
  question.setAttribute("aria-describedby", "system-question-message");
  question.innerHTML = `<form><header><div><small>FACULDADEMARIA</small><h2 id="system-question-title">Confirmar ação</h2></div><button type="button" data-cancel-question aria-label="Fechar">×</button></header><p id="system-question-message"></p><label id="system-question-field">Valor<input name="answer" inputmode="decimal" autocomplete="off"></label><footer><button type="button" data-cancel-question>Cancelar</button><button type="submit">Confirmar</button></footer></form>`;
  document.body.append(question);
  const queue = [];
  let active;
  function next() {
    if (active || !queue.length) return;
    active = queue.shift();
    question.querySelector("h2").textContent =
      active.kind === "prompt" ? "Informar valor" : "Confirmar ação";
    question.querySelector("#system-question-message").textContent =
      active.message;
    question.querySelector("#system-question-field").hidden =
      active.kind !== "prompt";
    question.querySelector("input").value = active.value;
    question.returnValue = "";
    question.showModal();
    question
      .querySelector(
        active.kind === "prompt" ? "input" : "[data-cancel-question]",
      )
      .focus();
    if (active.kind === "prompt") question.querySelector("input").select();
  }
  question.querySelector("form").onsubmit = (event) => {
    event.preventDefault();
    question.close("confirm");
  };
  question.querySelectorAll("[data-cancel-question]").forEach((button) => {
    button.onclick = () => question.close("cancel");
  });
  question.addEventListener("close", () => {
    if (!active) return;
    const current = active;
    active = null;
    current.resolve(
      question.returnValue === "confirm"
        ? current.kind === "prompt"
          ? question.querySelector("input").value
          : true
        : current.kind === "prompt"
          ? null
          : false,
    );
    next();
  });
  const ask = (kind, message, value = "") =>
    new Promise((resolve) => {
      queue.push({
        kind,
        message: String(message),
        value: String(value),
        resolve,
      });
      next();
    });
  window.FMDialogs = {
    confirm: (message) => ask("confirm", message),
    prompt: (message, value) => ask("prompt", message, value),
  };
  const scan = () =>
    document.querySelectorAll("dialog, .ccx-dialog").forEach(attach);
  scan();
  new MutationObserver((records) => {
    for (const record of records) {
      if (record.type === "childList") scan();
      if (record.type === "attributes") {
        if (record.target.matches("dialog")) reset(record.target);
        else if (record.target.matches(".ccx-modal"))
          record.target.querySelectorAll(".ccx-dialog").forEach(reset);
      }
    }
  }).observe(document.body, {
    subtree: true,
    childList: true,
    attributes: true,
    attributeFilter: ["open", "hidden"],
  });
  addEventListener("resize", () => popups.forEach((_, popup) => reset(popup)));
})();
