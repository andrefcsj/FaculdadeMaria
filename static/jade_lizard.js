(() => {
  const dialog = document.querySelector('#jadeDialog');
  const target = document.querySelector('#jadeCompare');
  if (!dialog || !target) return;
  const money = value => Number(value).toLocaleString('pt-BR', {style:'currency', currency:'BRL'});
  document.querySelectorAll('.jade-open').forEach(button => button.addEventListener('click', () => {
    const data = JSON.parse(button.closest('tr').dataset.jade);
    const putCapital = Math.max(0, (data.put_strike - data.put_credit) * 100);
    const putRoi = putCapital ? data.put_credit * 100 / putCapital * 100 : 0;
    target.innerHTML = `<h2 class="compare-title">${data.ticker}: Venda de PUT vs Jade Lizard</h2>
      <div class="compare-grid"><section class="compare-card"><h3>Venda de PUT</h3>${rows([
        ['Prêmio recebido', money(data.put_credit * 100)], ['Capital exigido', money(putCapital)],
        ['ROI', putRoi.toFixed(2) + '%'], ['Break-even', money(data.put_strike-data.put_credit)],
        ['Lucro máximo', money(data.put_credit*100)], ['Perda máxima', money(putCapital)], ['Capital em risco', money(putCapital)]
      ])}</section><section class="compare-card jade"><h3>Jade Lizard · Score ${data.score}</h3>${rows([
        ['Prêmio recebido', money(data.net_credit * 100)], ['Capital exigido', money(data.capital_required)],
        ['ROI', data.roi.toFixed(2) + '%'], ['Break-even', money(data.break_even)],
        ['Lucro máximo', money(data.max_profit)], ['Perda máxima', money(data.max_loss)],
        ['Capital em risco', money(data.capital_required)], ['Diferença de prêmio', '+' + (data.retention_pct-100).toFixed(1) + '%']
      ])}</section></div><div class="legs"><strong>Estrutura sugerida</strong><p>Vender ${data.put_code} · Vender ${data.short_call_code} · Comprar ${data.long_call_code}</p><small>Dados estimados: valide preços, liquidez e gregas na corretora.</small></div>
      <a class="mount-jade" style="display:block;text-align:center;text-decoration:none;margin-bottom:8px" href="/estrategias/simulador-payoff?asset=${encodeURIComponent(data.ticker)}&spot=${data.spot}&put=${encodeURIComponent(data.put_code)}&put_strike=${data.put_strike}&put_premium=${data.put_credit}&short_call=${encodeURIComponent(data.short_call_code)}&short_call_strike=${data.short_call_strike}&short_call_premium=${data.short_call_credit}&long_call=${encodeURIComponent(data.long_call_code)}&long_call_strike=${data.long_call_strike}&long_call_premium=${data.long_call_debit}">Simular Payoff</a><button class="mount-jade" type="button">Montar Operação</button>`;
    target.querySelector('.mount-jade').addEventListener('click', async event => {
      event.currentTarget.disabled = true;
      const response = await fetch('/api/estrategias/jade-lizard/montar', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
      const plan = await response.json();
      event.currentTarget.textContent = plan.ok ? '✓ Plano preparado — confirme na corretora' : plan.error;
    });
    dialog.showModal();
  }));
  function rows(items){ return items.map(([label,value]) => `<div class="metric"><span>${label}</span><strong>${value}</strong></div>`).join(''); }
  dialog.querySelector('.dialog-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
})();
