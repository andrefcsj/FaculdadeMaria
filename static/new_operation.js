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
  const coverageHint = q('newCoverageHint');
  const previewRoi = q('newPreviewRoi');
  const previewRoiHint = q('newPreviewRoiHint');
  const previewExercise = q('newPreviewExercise');
  const previewExerciseHint = q('newPreviewExerciseHint');
  const averageCostBox = q('newAverageCostBox');
  const averageCost = q('newAverageCost');
  const params = new URLSearchParams(location.search);

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
    if (normalized.startsWith('CPLE')) return 'CPLE3';
    const match = normalized.match(/^([A-Z]{4})(\d)/);
    return match ? `${match[1]}${match[2]}` : normalized.slice(0, 5);
  };
  const saveLabel = () => window.brokerageNoteImport?.buttonLabel?.() || '＋ Cadastrar operação';

  const setTone = (element, tone) => {
    element.classList.remove('is-good', 'is-medium', 'is-low', 'is-unavailable');
    element.classList.add(tone);
  };

  const updateRoiPreview = () => {
    const strategy = form.querySelector('input[name="Estrategia"]:checked')?.value;
    const quantity = Math.max(num(fields.contracts.value), 0) * 100;
    const strike = num(fields.strike.value);
    const premium = num(fields.premium.value);
    if (strategy === 'Compra') {
      previewRoi.textContent = '--';
      setTone(previewRoi, 'is-unavailable');
      previewRoiHint.textContent = 'Na compra, o retorno depende do preço de saída da opção.';
      return;
    }
    if (!quantity || !strike || !premium) {
      previewRoi.textContent = '--';
      setTone(previewRoi, 'is-unavailable');
      previewRoiHint.textContent = 'Preencha strike, prêmio e quantidade.';
      return;
    }
    const netPremium = premium * quantity - num(fields.costs.value) - num(fields.irrf.value);
    const roi = netPremium / (strike * quantity) * 100;
    previewRoi.textContent = `${roi.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}%`;
    setTone(previewRoi, roi >= 2 ? 'is-good' : roi >= 1 ? 'is-medium' : 'is-low');
    previewRoiHint.textContent = 'Prêmio líquido dividido pelo capital nominal no strike.';
  };

  let previewTimer;
  let previewSequence = 0;
  const scheduleProbabilityPreview = () => {
    clearTimeout(previewTimer);
    const strike = num(fields.strike.value);
    if (!strike || !fields.expiry.value || !(fields.under.value || infer(fields.code.value))) {
      previewExercise.textContent = '--';
      setTone(previewExercise, 'is-unavailable');
      previewExerciseHint.textContent = 'Preencha cotação, strike e vencimento.';
      return;
    }
    const sequence = ++previewSequence;
    previewExercise.textContent = '…';
    setTone(previewExercise, 'is-unavailable');
    previewExerciseHint.textContent = 'Calculando com volatilidade histórica...';
    previewTimer = setTimeout(async () => {
      try {
        const response = await fetch('/api/operacoes/preview', {
          method: 'POST',
          headers: {'Content-Type': 'application/json', Accept: 'application/json'},
          body: JSON.stringify({
            Ativo: fields.code.value.trim().toUpperCase(),
            Ativo_subjacente: fields.under.value.trim().toUpperCase(),
            Tipo: form.querySelector('input[name="Tipo"]:checked')?.value || 'PUT',
            Estrategia: form.querySelector('input[name="Estrategia"]:checked')?.value || 'Venda',
            Contratos: fields.contracts.value,
            Strike: rawMoney(fields.strike.value),
            Premio_opcao: rawMoney(fields.premium.value),
            Vencimento: fields.expiry.value,
            Cotacao_atual: rawMoney(fields.spot.value),
            Custos: rawMoney(fields.costs.value),
            IRRF: rawMoney(fields.irrf.value)
          })
        });
        const data = await response.json();
        if (!response.ok || !data.ok) throw new Error(data.error || 'Estimativa indisponível');
        if (sequence !== previewSequence) return;
        if (data.underlying && fields.code.value.trim().toUpperCase().startsWith('CPLE')) fields.under.value = 'CPLE3';
        previewExercise.textContent = data.exercise_probability || '--';
        const probability = num(String(data.exercise_probability || '').replace('%', ''));
        setTone(previewExercise, data.exercise_probability === '--' ? 'is-unavailable' : probability >= 65 ? 'is-low' : probability >= 35 ? 'is-medium' : 'is-good');
        previewExerciseHint.textContent = `${data.exercise_label}. ${data.exercise_methodology}`;
      } catch (_error) {
        if (sequence !== previewSequence) return;
        previewExercise.textContent = '--';
        setTone(previewExercise, 'is-unavailable');
        previewExerciseHint.textContent = 'Estimativa temporariamente indisponível; os demais cálculos continuam válidos.';
      }
    }, 550);
  };

  let holdingsPromise;
  let averageCostSequence = 0;
  const syncAverageCost = async () => {
    const sequence = ++averageCostSequence;
    const isSale = form.querySelector('input[name="Estrategia"]:checked')?.value === 'Venda';
    const isCall = form.querySelector('input[name="Tipo"]:checked')?.value === 'CALL';
    const asset = (fields.under.value || infer(fields.code.value)).trim().toUpperCase();
    if (!isSale || !isCall || !asset) {
      averageCostBox.hidden = true;
      return;
    }
    const linkPrice = num(params.get('preco_medio'));
    if (linkPrice > 0) {
      averageCost.textContent = brl(linkPrice);
      averageCostBox.hidden = false;
    }
    try {
      holdingsPromise ||= fetch('/api/carteira-acoes').then(response => response.json());
      const data = await holdingsPromise;
      if (sequence !== averageCostSequence) return;
      const holding = data.holdings?.find(item => String(item.asset).toUpperCase() === asset);
      const portfolioPrice = num(holding?.tax_cost_per_share);
      if (portfolioPrice > 0) {
        averageCost.textContent = brl(portfolioPrice);
        averageCostBox.hidden = false;
      } else if (!linkPrice) {
        averageCostBox.hidden = true;
      }
    } catch (_error) {
      if (sequence === averageCostSequence && !linkPrice) averageCostBox.hidden = true;
    }
  };

  const updateSummary = () => {
    const code = fields.code.value.trim().toUpperCase();
    const underlying = fields.under.value || infer(code);
    const quantity = Math.max(num(fields.contracts.value), 0) * 100;
    const total = Math.max(num(fields.premium.value), 0) * quantity;
    const strategy = form.querySelector('input[name="Estrategia"]:checked')?.value;
    const isPurchase = strategy === 'Compra';
    if (code.startsWith('CPLE') || !fields.under.value) fields.under.value = underlying;
    summaryCode.textContent = code || 'Nova operação';
    summaryDetails.textContent = `${underlying || 'Ativo'} • ${quantity || 0} ações • Strike ${brl(num(fields.strike.value))}`;
    summaryValueLabel.textContent = isPurchase ? 'Débito bruto estimado' : 'Prêmio bruto estimado';
    summaryPremium.textContent = brl(total);
    summaryPremium.classList.toggle('is-debit', isPurchase);
    updateRoiPreview();
    scheduleProbabilityPreview();
    syncAverageCost();
  };

  document.querySelectorAll('.new-money').forEach(input => {
    input.addEventListener('blur', event => {
      event.target.value = brl(num(event.target.value));
      updateSummary();
    });
  });
  ['input', 'change'].forEach(eventName => {
    [fields.code, fields.under, fields.strike, fields.contracts, fields.premium, fields.expiry, fields.spot, fields.costs, fields.irrf].forEach(input => input.addEventListener(eventName, updateSummary));
  });
  form.querySelectorAll('input[name="Estrategia"]').forEach(input => input.addEventListener('change', updateSummary));
  form.querySelectorAll('input[name="Tipo"]').forEach(input => input.addEventListener('change', updateSummary));

  let lookupTimer;
  let lookupSequence = 0;
  fields.code.addEventListener('input', () => {
    clearTimeout(lookupTimer);
    const sequence = ++lookupSequence;
    if (fields.code.value.trim().toUpperCase().startsWith('CPLE') || !fields.under.value) fields.under.value = infer(fields.code.value);
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
        fields.under.value = code.startsWith('CPLE') ? 'CPLE3' : (data.asset || infer(code));
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
  if (params.get('estrategia') === 'coberta') {
    q('newVenda').checked = true;
    q('newCall').checked = true;
    fields.under.value = String(params.get('ativo') || '').toUpperCase();
    coverageHint.textContent = 'A cobertura será validada automaticamente pelas ações livres da carteira.';
    const linkPrice = num(params.get('preco_medio'));
    if (linkPrice > 0) {
      averageCostBox.hidden = false;
      averageCost.textContent = brl(linkPrice);
    }
    updateSummary();
  }
  if (location.hash === '#nova-operacao' || params.get('nova') === '1') openModal();
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !modal.hidden) closeModal();
  });

  form.addEventListener('submit', async event => {
    event.preventDefault();
    errorBox.style.display = 'none';
    if (!form.reportValidity()) return;
    let payload = {
      Ativo: fields.code.value.trim().toUpperCase(),
      Ativo_subjacente: fields.under.value.trim().toUpperCase(),
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
      if (location.pathname === '/operacoes-abertas' || location.pathname === '/carteira-acoes') location.reload();
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
