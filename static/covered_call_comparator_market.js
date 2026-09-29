(() => {
  const modal = document.getElementById('coveredCallComparatorModal');
  if (!modal) return;
  const asset = document.getElementById('ccxAsset');
  const preview = document.getElementById('ccxAssetPreview');
  const logo = document.getElementById('ccxAssetLogo');
  const name = document.getElementById('ccxAssetName');
  const spot = document.getElementById('ccxSpot');
  const calls = document.getElementById('ccxCalls');
  const parse = value => Number(String(value ?? '').replace(',', '.')) || 0;
  const format = value => Number(value).toFixed(2).replace('.', ',');
  const currentAsset = () => asset.value.trim().toUpperCase().replace(/\.SA$/, '');
  const showAsset = () => {
    asset.value = currentAsset();
    const ticker = currentAsset();
    const valid = /^[A-Z]{4}\d{1,2}$/.test(ticker);
    preview.hidden = !valid;
    if (!valid) return;
    name.textContent = ticker;
    logo.alt = `${ticker} · logo do ativo`;
    logo.src = `https://raw.githubusercontent.com/thefintz/icones-b3/main/icones/${encodeURIComponent(ticker)}.png`;
  };
  asset.addEventListener('input', showAsset);
  logo.addEventListener('error', () => { preview.hidden = true; }, { once: false });
  let timer;
  async function lookup(input) {
    const card = input.closest('.ccx-call');
    const status = card.querySelector('[data-ccx-status]');
    const ticker = currentAsset();
    const code = input.value.trim().toUpperCase().replace(/\.SA$/, '');
    input.value = code;
    if (!ticker || !code || code.length < 5) return;
    status.textContent = 'Consultando mercado…';
    try {
      const response = await fetch(`/api/comparador-call-coberta/opcao?ativo=${encodeURIComponent(ticker)}&codigo=${encodeURIComponent(code)}`);
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.message || 'Não foi possível consultar esta CALL.');
      const option = payload.option;
      card.querySelector('[data-ccx=strike]').value = format(option.strike);
      card.querySelector('[data-ccx=premium]').value = format(option.premium);
      const expiry = card.querySelector('[data-ccx=expiry]');
      if (expiry) expiry.value = option.expiry;
      if (!parse(spot.value) && option.spot) spot.value = format(option.spot);
      status.textContent = `Dados carregados · ${option.source}`;
    } catch (error) {
      status.textContent = error.message;
    }
  }
  calls.addEventListener('input', event => {
    if (event.target.dataset.ccx !== 'code') return;
    clearTimeout(timer);
    timer = setTimeout(() => lookup(event.target), 650);
  });
  calls.addEventListener('change', event => {
    if (event.target.dataset.ccx === 'code') lookup(event.target);
  });
})();
