document.addEventListener('DOMContentLoaded', () => {
  const modal = document.getElementById('newOperationModal');
  const form = document.getElementById('newOperationForm');
  if (!modal || !form) return;

  const q = id => document.getElementById(id);
  const fields = {
    code: q('newOptionCode'),
    under: q('newUnderlying'),
    strike: q('newStrike'),
    contracts: q('newContracts'),
    premium: q('newPremium'),
    expiry: q('newExpiry'),
    spot: q('newSpot'),
    costs: q('newCosts'),
    irrf: q('newIrrf')
  };
  const errorBox = q('newOperationError');
  const saveButton = q('newOperationSave');
  const summaryCode = q('newSummaryCode');
  const summaryDetails = q('newSummaryDetails');
  const summaryPremium = q('newSummaryPremium');
  const summaryValueLabel = q('newSummaryValueLabel');
  const hint = q('newOptionHint');

  const num = value => {
    let text = String(value || '').replace('R$', '').replace(/\s/g, '');
    if (text.includes(',') && text.includes('.')) text = text.replace(/\./g, '').replace(',', '.');
    else text = text.replace(',', '.');
    return Number(text) || 0;
  };
  const brl = value => new Intl.NumberFormat('pt-BR', {style: 'currency', currency: 'BRL'}).format(Number(value) || 0);
  const rawMoney = value => String(num(value));
  const infer = code => {
    const normalized = String(code || '').trim().toUpperCase();
    const match = normalized.match(/^([A-Z]{4})(\d)/);
    return match ? `${match[1]}${match[2]}` : normalized.slice(0, 5);
  };
  const saveLabel = () => window.brokerageNoteImport?.buttonLabel?.() || '＋ Cadastrar operação';

  const updateSummary = () => {
    const code = fields.code.value.trim().toUpperCase();
    const underlying = fields.under.value || infer(code);
    const quantity = Math.max(num(fields.contracts.value), 0) * 100;
    const total = Math.max(num(fields.premium.value), 0) * quantity;
    const isPurchase = form.querySelector('input[name="Estrategia"]:checked')?.value === 'Compra';
    fields.under.value = underlying;
    summaryCode.textContent = code || 'Nova operação';
    summaryDetails.textContent = `${underlying || 'Ativo'} • ${quantity || 0} ações • Strike ${brl(num(fields.strike.value))}`;
    summaryValueLabel.textContent = isPurchase ? 'Débito bruto estimado' : 'Prêmio bruto estimado';
    summaryPremium.textContent = brl(total);
    summaryPremium.classList.toggle('is-debit', isPurchase);
  };

  document.querySelectorAll('.new-money').forEach(input => {
    input.addEventListener('blur', event => {
      event.target.value = brl(num(event.target.value));
      updateSummary();
    });
  });
  ['input', 'change'].forEach(eventName => {
    [fields.code, fields.strike, fields.contracts, fields.premium].forEach(input => input.addEventListener(eventName, updateSummary));
  });
  form.querySelectorAll('input[name="Estrategia"]').forEach(input => input.addEventListener('change', updateSummary));

  let lookupTimer;
  let lookupSequence = 0;
  fields.code.addEventListener('input', () => {
    clearTimeout(lookupTimer);
    const sequence = ++lookupSequence;
    fields.under.value = infer(fields.code.value);
    updateSummary();
    lookupTimer = setTimeout(async () => {
      const code = fields.code.value.trim().toUpperCase();
      if (code.length < 5) return;
      hint.textContent = 'Buscando dados da opção...';
      try {
        const response = await fetch(`/api/opcoes/${encodeURIComponent(code)}`);
        const data = await response.json();
        if (!response.ok || !data.ok) throw new Error(data.error || 'Falha na consulta');
        if (sequence !== lookupSequence || fields.code.value.trim().toUpperCase() !== code) return;
        fields.under.value = data.asset || infer(code);
        if (data.strike) fields.strike.value = brl(num(data.strike));
        if (data.expiry) fields.expiry.value = data.expiry;
        if (data.premium) fields.premium.value = brl(num(data.premium));
        if (data.spot_price) fields.spot.value = brl(num(data.spot_price));
        hint.textContent = `Dados preenchidos via ${data.source}.`;
        updateSummary();
      } catch (_error) {
        if (sequence !== lookupSequence || fields.code.value.trim().toUpperCase() !== code) return;
        hint.textContent = 'Ativo identificado. Strike e vencimento devem ser informados manualmente.';
      }
    }, 450);
  });

  const openModal = () => {
    modal.hidden = false;
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    setTimeout(() => fields.code.focus(), 50);
  };
  const closeModal = () => {
    modal.hidden = true;
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    errorBox.style.display = 'none';
  };
  document.addEventListener('click', event => {
    const openButton = event.target.closest('[data-open-new-operation]');
    if (openButton) {
      event.preventDefault();
      openModal();
      return;
    }
    if (event.target.closest('[data-new-op-close]')) closeModal();
  });
  if (location.hash === '#nova-operacao' || new URLSearchParams(location.search).get('nova') === '1') openModal();
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !modal.hidden) closeModal();
  });

  form.addEventListener('submit', async event => {
    event.preventDefault();
    errorBox.style.display = 'none';
    if (!form.reportValidity()) return;
    let payload = {
      Ativo: fields.code.value.trim().toUpperCase(),
      Tipo: form.querySelector('input[name="Tipo"]:checked')?.value || 'PUT',
      Estrategia: form.querySelector('input[name="Estrategia"]:checked')?.value || 'Venda',
      Contratos: fields.contracts.value,
      Strike: rawMoney(fields.strike.value),
      Premio_opcao: rawMoney(fields.premium.value),
      Vencimento: fields.expiry.value,
      Cotacao_atual: rawMoney(fields.spot.value),
      Custos: rawMoney(fields.costs.value),
      IRRF: rawMoney(fields.irrf.value),
      Interesse_exercicio: form.querySelector('input[name="Interesse_exercicio"]:checked')?.value === 'true'
    };
    payload = window.brokerageNoteImport?.preparePayload?.(payload) || payload;
    saveButton.disabled = true;
    saveButton.textContent = 'Salvando...';
    try {
      const response = await fetch('/api/operacoes', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', Accept: 'application/json'},
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error || 'Não foi possível cadastrar.');
      if (window.brokerageNoteImport?.handleSaved?.()) {
        updateSummary();
        return;
      }
      window.brokerageNoteImport?.finish?.();
      closeModal();
      form.reset();
      fields.contracts.value = '1';
      fields.costs.value = brl(0);
      fields.irrf.value = brl(0);
      if (location.pathname === '/operacoes-abertas') location.reload();
      else window.dispatchEvent(new CustomEvent('operation-created', {detail: data}));
    } catch (error) {
      errorBox.textContent = error.message;
      errorBox.style.display = 'block';
    } finally {
      saveButton.disabled = false;
      saveButton.textContent = saveLabel();
    }
  });

  updateSummary();
});
