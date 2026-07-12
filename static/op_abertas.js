document.addEventListener('DOMContentLoaded', () => {
  const search = document.getElementById('buscaAtivo');
  const modal = document.getElementById('editOperationModal');
  const form = document.getElementById('editOperationForm');
  const errorBox = document.getElementById('editError');
  const saveButton = document.getElementById('saveOperationButton');
  const fields = {
    id: document.getElementById('editId'), underlying: document.getElementById('editUnderlying'),
    option: document.getElementById('editAtivo'), strike: document.getElementById('editStrike'),
    contracts: document.getElementById('editContratos'), premium: document.getElementById('editPremio'),
    expiry: document.getElementById('editVencimento'), spot: document.getElementById('editCotacao'),
    status: document.getElementById('editStatus'), costs: document.getElementById('editCustos'), irrf: document.getElementById('editIrrf')
  };
  const moneyFields = [fields.strike, fields.premium, fields.spot, fields.costs, fields.irrf].filter(Boolean);
  const summaryCode = document.getElementById('summaryCode');
  const summaryDetails = document.getElementById('summaryDetails');
  const summaryPremium = document.getElementById('summaryPremium');
  const premiumTotal = document.getElementById('premiumTotal');
  const summaryLogo = document.getElementById('summaryLogo');
  const summaryLogoFallback = document.getElementById('summaryLogoFallback');

  const parseNumber = (value) => {
    const text = String(value ?? '').replace(/R\$/g, '').replace(/\s/g, '');
    if (!text) return 0;
    if (text.includes(',') && text.includes('.')) return Number(text.replace(/\./g, '').replace(',', '.')) || 0;
    return Number(text.replace(',', '.')) || 0;
  };
  const formatMoney = (value) => new Intl.NumberFormat('pt-BR', {style: 'currency', currency: 'BRL'}).format(Number.isFinite(Number(value)) ? Number(value) : 0);
  const toIsoDate = (value) => { const t = String(value ?? '').trim(); if (/^\d{4}-\d{2}-\d{2}$/.test(t)) return t; const m = t.match(/^(\d{2})\/(\d{2})\/(\d{4})$/); return m ? `${m[3]}-${m[2]}-${m[1]}` : t; };
  const inferUnderlying = (code) => { const c = String(code ?? '').trim().toUpperCase(); const m = c.match(/^([A-Z]{4})(\d)/); return m ? `${m[1]}${m[2]}` : c.slice(0, 5); };
  const setChecked = (name, value, fallback) => { const normalized = String(value || fallback).toUpperCase(); const radios = form.querySelectorAll(`input[name="${name}"]`); radios.forEach(r => r.checked = r.value.toUpperCase() === normalized); if (![...radios].some(r => r.checked) && radios[0]) radios[0].checked = true; };

  const showAssetLogo = (url, ticker) => {
    if (!summaryLogo || !summaryLogoFallback) return;
    summaryLogoFallback.textContent = (ticker || '--').slice(0, 2);
    if (!url) { summaryLogo.style.display = 'none'; summaryLogoFallback.style.display = 'flex'; return; }
    summaryLogo.style.display = 'block'; summaryLogoFallback.style.display = 'none'; summaryLogo.src = url;
    summaryLogo.onerror = () => { summaryLogo.style.display = 'none'; summaryLogoFallback.style.display = 'flex'; };
  };

  const updateSummary = () => {
    const code = fields.option?.value.trim().toUpperCase() || 'Opção';
    const contracts = Math.max(parseNumber(fields.contracts?.value), 0);
    const premium = Math.max(parseNumber(fields.premium?.value), 0);
    const strike = Math.max(parseNumber(fields.strike?.value), 0);
    const quantity = contracts * 100;
    const underlying = fields.underlying?.value || inferUnderlying(code);
    if (fields.underlying && !fields.underlying.value) fields.underlying.value = underlying;
    if (summaryCode) summaryCode.textContent = `${underlying || '--'} • ${code}`;
    if (summaryDetails) summaryDetails.textContent = `${quantity || 0} ações • Strike ${formatMoney(strike)}`;
    if (summaryPremium) summaryPremium.textContent = formatMoney(premium * quantity);
    if (premiumTotal) premiumTotal.textContent = `Total estimado: ${formatMoney(premium * quantity)}`;
  };

  const showError = (message) => { if (errorBox) { errorBox.textContent = message; errorBox.style.display = 'block'; } };
  const clearError = () => { if (errorBox) { errorBox.textContent = ''; errorBox.style.display = 'none'; } };
  const openModal = () => { if (!modal) return; modal.hidden = false; modal.setAttribute('aria-hidden', 'false'); document.body.style.overflow = 'hidden'; setTimeout(() => fields.option?.focus(), 50); };
  const closeModal = () => { if (!modal) return; modal.hidden = true; modal.setAttribute('aria-hidden', 'true'); document.body.style.overflow = ''; clearError(); };
  const formatAllMoney = () => moneyFields.forEach(field => { field.value = formatMoney(parseNumber(field.value)); });

  const loadOperation = async (id) => {
    clearError(); if (saveButton) saveButton.disabled = true;
    try {
      const response = await fetch(`/api/operacoes/${encodeURIComponent(id)}`, {headers: {Accept: 'application/json'}});
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.error || 'Não foi possível carregar a operação.');
      const o = payload.operation;
      fields.id.value = o.ID; fields.option.value = o.Ativo || ''; fields.underlying.value = o.Ativo_subjacente || inferUnderlying(o.Ativo);
      fields.strike.value = formatMoney(parseNumber(o.Strike)); fields.contracts.value = o.Contratos || '1'; fields.premium.value = formatMoney(parseNumber(o.Premio_opcao));
      fields.expiry.value = toIsoDate(o.Vencimento || ''); fields.spot.value = formatMoney(parseNumber(o.Cotacao_atual)); fields.status.value = o.Status || 'Aberta';
      fields.costs.value = formatMoney(parseNumber(o.Custos)); fields.irrf.value = formatMoney(parseNumber(o.IRRF));
      setChecked('Tipo', o.Tipo, 'PUT'); setChecked('Estrategia', o.Estrategia, 'Venda');
      showAssetLogo(o.Logo_subjacente, fields.underlying.value); updateSummary(); openModal();
    } catch (error) { window.alert(error.message || 'Não foi possível abrir a edição.'); }
    finally { if (saveButton) saveButton.disabled = false; }
  };

  search?.addEventListener('input', () => { const term = search.value.toLowerCase(); document.querySelectorAll('#tabelaOperacoes tbody tr').forEach(row => row.style.display = row.innerText.toLowerCase().includes(term) ? '' : 'none'); });
  document.addEventListener('click', (event) => {
    const edit = event.target.closest('[data-edit-id]'); if (edit) { event.preventDefault(); loadOperation(edit.dataset.editId); return; }
    if (event.target.closest('[data-modal-close]')) { closeModal(); return; }
    const del = event.target.closest('.btn-action.delete'); if (del && !window.confirm('Tem certeza que deseja excluir esta operação?')) { event.preventDefault(); event.stopPropagation(); }
  });
  document.addEventListener('keydown', event => { if (event.key === 'Escape' && modal && !modal.hidden) closeModal(); });

  moneyFields.forEach(field => {
    field.addEventListener('focus', () => { field.value = parseNumber(field.value).toFixed(2).replace('.', ','); field.select(); });
    field.addEventListener('blur', () => { field.value = formatMoney(parseNumber(field.value)); updateSummary(); });
  });
  ['input', 'change'].forEach(evt => ['editAtivo', 'editContratos', 'editPremio', 'editStrike'].forEach(id => document.getElementById(id)?.addEventListener(evt, updateSummary)));

  form?.addEventListener('submit', async (event) => {
    event.preventDefault(); clearError(); if (!form.reportValidity()) return;
    const id = fields.id.value;
    const payload = {
      Ativo: fields.option.value.trim().toUpperCase(), Tipo: form.querySelector('input[name="Tipo"]:checked')?.value || 'PUT',
      Estrategia: form.querySelector('input[name="Estrategia"]:checked')?.value || 'Venda', Status: fields.status.value,
      Contratos: fields.contracts.value, Strike: String(parseNumber(fields.strike.value)), Premio_opcao: String(parseNumber(fields.premium.value)),
      Custos: String(parseNumber(fields.costs.value)), IRRF: String(parseNumber(fields.irrf.value)), Vencimento: fields.expiry.value,
      Cotacao_atual: String(parseNumber(fields.spot.value))
    };
    if (saveButton) { saveButton.disabled = true; saveButton.textContent = 'Salvando...'; }
    try {
      const response = await fetch(`/api/operacoes/${encodeURIComponent(id)}`, {method: 'POST', headers: {'Content-Type': 'application/json', Accept: 'application/json'}, body: JSON.stringify(payload)});
      const result = await response.json(); if (!response.ok || !result.ok) throw new Error(result.error || 'Não foi possível salvar a operação.');
      closeModal(); window.location.reload();
    } catch (error) { showError(error.message || 'Erro inesperado ao salvar.'); formatAllMoney(); }
    finally { if (saveButton) { saveButton.disabled = false; saveButton.textContent = 'Salvar alterações'; } }
  });
});


document.addEventListener('DOMContentLoaded',()=>{
  const modal=document.getElementById('closeOperationModal');
  const form=document.getElementById('closeOperationForm');
  if(!modal || !form) return;

  const methodInput=document.getElementById('closeMethod');
  const dateInput=document.getElementById('closeDate');
  const repurchase=document.getElementById('repurchaseValue');
  const repurchaseField=document.getElementById('repurchaseField');
  const resultOutput=document.getElementById('closeResult');
  const errorBox=document.getElementById('closeError');
  const hint=document.getElementById('closeMethodHint');
  const expiredMethod=document.getElementById('expiredMethod');
  let operation={};

  const brl=value=>Number(value||0).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
  const today=()=>new Date().toISOString().slice(0,10);
  const hints={
    recompra:'↻ Posição zerada com lucro/prejuízo na recompra.',
    exercida:'ϟ Exercício faz parte da estratégia; o prêmio recebido é preservado.',
    cancelada:'⊗ Registro encerrado por cancelamento ou correção operacional.',
    virou_po:'✧ Opção expirada sem valor; prêmio integral preservado.'
  };

  function calculateResult(){
    const method=methodInput.value;
    const premium=Number(operation.premiumTotal||0);
    const buyback=Number(repurchase.value||0)*Number(operation.contracts||0)*Number(operation.contractSize||0);
    const result=method==='recompra'?premium-buyback:method==='cancelada'?0:premium;
    resultOutput.value=brl(result);
    resultOutput.textContent=brl(result);
    resultOutput.classList.toggle('close-result--positive',result>0);
    resultOutput.classList.toggle('close-result--negative',result<0);
  }

  function updateExpiredAvailability(){
    const allowed=!operation.expiry || dateInput.value>=operation.expiry;
    expiredMethod.classList.toggle('is-disabled',!allowed);
    expiredMethod.disabled=!allowed;
    if(!allowed && methodInput.value==='virou_po') selectMethod('recompra');
  }

  function selectMethod(method){
    const selected=form.querySelector(`[data-method="${method}"]`);
    if(!selected || selected.disabled) return;
    methodInput.value=method;
    form.querySelectorAll('.close-method').forEach(button=>button.classList.toggle('active',button===selected));
    repurchaseField.style.opacity=method==='recompra'?'1':'.5';
    repurchase.disabled=method!=='recompra';
    repurchase.required=method==='recompra';
    hint.textContent=hints[method];
    errorBox.hidden=true;
    calculateResult();
  }

  function openModal(button){
    operation={
      closeUrl:button.dataset.closeUrl,
      option:button.dataset.option,
      ticker:button.dataset.ticker,
      type:button.dataset.type,
      strategy:button.dataset.strategy,
      strike:Number(button.dataset.strike||0),
      expiry:button.dataset.expiry,
      expiryLabel:button.dataset.expiryLabel,
      contracts:Number(button.dataset.contracts||0),
      contractSize:Number(button.dataset.contractSize||100),
      premiumTotal:Number(button.dataset.premiumTotal||0)
    };
    form.action=operation.closeUrl;
    document.getElementById('closeAssetLetter').textContent=(operation.ticker||operation.option||'?').slice(0,1);
    document.getElementById('closeOperationDescription').textContent=`${operation.option} · ${operation.strategy} ${operation.type} · strike ${brl(operation.strike)} · venc. ${operation.expiryLabel||'—'}`;
    dateInput.value=today();
    repurchase.value='0.00';
    modal.hidden=false;
    modal.setAttribute('aria-hidden','false');
    document.body.classList.add('close-modal-open');
    updateExpiredAvailability();
    selectMethod('recompra');
    setTimeout(()=>repurchase.focus(),80);
  }

  function closeModal(){
    modal.hidden=true;
    modal.setAttribute('aria-hidden','true');
    document.body.classList.remove('close-modal-open');
    errorBox.hidden=true;
  }

  document.addEventListener('click',event=>{
    const closeButton=event.target.closest('.js-open-close-modal');
    if(closeButton){event.preventDefault();openModal(closeButton);return;}
    if(event.target.closest('[data-close-modal]')){event.preventDefault();closeModal();return;}
    const methodButton=event.target.closest('.close-method');
    if(methodButton){selectMethod(methodButton.dataset.method);return;}
  });
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!modal.hidden)closeModal();});
  repurchase.addEventListener('input',calculateResult);
  dateInput.addEventListener('change',updateExpiredAvailability);

  form.addEventListener('submit',async event=>{
    event.preventDefault();
    errorBox.hidden=true;
    const confirmButton=form.querySelector('.close-confirm');
    confirmButton.disabled=true;
    confirmButton.textContent='Encerrando...';
    try{
      const response=await fetch(form.action,{method:'POST',body:new FormData(form),headers:{'X-Requested-With':'XMLHttpRequest'}});
      const data=await response.json();
      if(!response.ok||!data.ok) throw new Error(data.message||'Não foi possível encerrar a operação.');
      window.location.assign(data.redirect||'/operacoes-abertas');
    }catch(error){
      errorBox.textContent=error.message;
      errorBox.hidden=false;
      confirmButton.disabled=false;
      confirmButton.textContent='✓ Confirmar encerramento';
    }
  });
});
