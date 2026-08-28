(() => {
  const modal = document.getElementById('quickRoi');
  if (!modal) return;
  const form = document.getElementById('quickRoiForm');
  const roi = document.getElementById('quickRoiValue');
  const distance = document.getElementById('quickRoiDistance');
  const direction = document.getElementById('quickRoiDirection');
  let opener;
  const number = value => {
    const raw = value.trim().replace(/\s|R\$/g, '');
    if (!raw) return NaN;
    const normalized = raw.includes(',') ? raw.replace(/\./g, '').replace(',', '.') : raw;
    return /^\d+(\.\d+)?$/.test(normalized) ? Number(normalized) : NaN;
  };
  const percent = value => `${value.toLocaleString('pt-BR', {minimumFractionDigits:2, maximumFractionDigits:2})}%`;
  function calculate() {
    const strike = number(form.elements.strike.value);
    const premium = number(form.elements.premium.value);
    const spot = number(form.elements.spot.value);
    const valid = value => Number.isFinite(value) && value > 0;
    const result = premium / strike * 100;
    roi.textContent = valid(strike) && Number.isFinite(premium) && premium >= 0 && Number.isFinite(result) ? percent(result) : '—';
    const gap = (strike / spot - 1) * 100;
    distance.textContent = valid(strike) && valid(spot) && Number.isFinite(gap) ? percent(gap) : '—';
    direction.textContent = distance.textContent === '—' ? '(Strike ÷ preço atual − 1) × 100' : gap < 0 ? 'Strike abaixo do preço atual' : gap > 0 ? 'Strike acima do preço atual' : 'Strike igual ao preço atual';
  }
  document.querySelectorAll('[data-open-quick-roi]').forEach(link => link.addEventListener('click', event => {
    event.preventDefault(); opener = link; modal.showModal(); calculate();
  }));
  modal.querySelectorAll('[data-close-quick-roi]').forEach(button => button.addEventListener('click', () => modal.close()));
  modal.addEventListener('close', () => opener?.focus());
  modal.addEventListener('click', event => { if (event.target === modal) { const r = modal.getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) modal.close(); } });
  form.addEventListener('input', calculate);
  form.addEventListener('submit', event => event.preventDefault());
  document.getElementById('quickRoiReset').addEventListener('click', () => { form.reset(); calculate(); form.elements.strike.focus(); });
})();
