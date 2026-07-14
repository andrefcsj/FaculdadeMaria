let brokerageLookupSequence = 0;

document.addEventListener('brokerage-trade-applied', async event => {
  const code = String(event.detail?.optionCode || '').trim().toUpperCase();
  if (!code) return;
  const sequence = ++brokerageLookupSequence;
  const q = id => document.getElementById(id);
  const hint = q('newOptionHint');
  const strike = q('newStrike');
  const expiry = q('newExpiry');
  const spot = q('newSpot');
  const under = q('newUnderlying');
  const optionCode = q('newOptionCode');
  const brl = value => new Intl.NumberFormat('pt-BR', {style: 'currency', currency: 'BRL'}).format(Number(value) || 0);

  // Nunca exibir dados estruturais deixados pela negociação anterior.
  if (strike) strike.value = '';
  if (expiry) expiry.value = '';
  if (spot) spot.value = '';
  if (under) under.value = '';
  if (hint) hint.textContent = 'Buscando strike e vencimento da opção importada...';

  try {
    const response = await fetch(`/api/opcoes/${encodeURIComponent(code)}`);
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || 'Consulta indisponível');
    if (sequence !== brokerageLookupSequence || optionCode?.value.trim().toUpperCase() !== code) return;
    if (data.asset && under) under.value = data.asset;
    if (data.strike && strike) strike.value = brl(data.strike);
    if (data.expiry && expiry) expiry.value = data.expiry;
    if (data.spot_price && spot) spot.value = brl(data.spot_price);
    if (hint) {
      hint.textContent = data.strike
        ? `Strike e vencimento preenchidos via ${data.source}.`
        : 'Código reconhecido, mas o strike não consta no mercado carregado. Informe-o manualmente.';
    }
    strike?.dispatchEvent(new Event('change', {bubbles: true}));
  } catch (_error) {
    if (sequence !== brokerageLookupSequence || optionCode?.value.trim().toUpperCase() !== code) return;
    if (hint) hint.textContent = 'Não foi possível localizar o strike. Atualize a B3/CSV ou confira manualmente.';
    strike?.dispatchEvent(new Event('change', {bubbles: true}));
  }
});
