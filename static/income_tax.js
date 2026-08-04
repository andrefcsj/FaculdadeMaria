(() => {
  const dialog = document.querySelector('#taxOperationsDialog');
  const body = document.querySelector('#taxDialogBody');
  const empty = document.querySelector('#taxDialogEmpty');
  const title = document.querySelector('#taxDialogTitle');
  if (!dialog || !body) return;
  const money = value => Number(value || 0).toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'});
  const date = value => {
    const parts = String(value || '').slice(0, 10).split('-');
    return parts.length === 3 ? `${parts[2]}/${parts[1]}/${parts[0]}` : (value || '—');
  };
  document.addEventListener('click', event => {
    const trigger = event.target.closest('.tax-detail-trigger');
    if (!trigger) return;
    event.preventDefault(); event.stopPropagation();
    let rows = [];
    try { rows = JSON.parse(trigger.dataset.operations || '[]'); } catch (_) {}
    title.textContent = `Operações tributadas · ${trigger.dataset.title || ''}`;
    body.replaceChildren(...rows.map(item => {
      const tr = document.createElement('tr');
      [item.option_code, date(item.open_date), date(item.close_date), item.modality, money(item.taxable_base), money(item.tax)].forEach(value => {
        const td = document.createElement('td'); td.textContent = value || '—'; tr.appendChild(td);
      });
      return tr;
    }));
    empty.hidden = rows.length > 0;
    dialog.showModal();
  });
  dialog.querySelector('[data-close-dialog]').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
})();
