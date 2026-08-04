(() => {
  const dialog = document.querySelector('#taxOperationsDialog');
  const body = document.querySelector('#taxDialogBody');
  const empty = document.querySelector('#taxDialogEmpty');
  const title = document.querySelector('#taxDialogTitle');
  const totals = document.querySelector('#taxDialogTotals');
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
      const logoCell = document.createElement('td');
      if (item.logo) {
        const img = document.createElement('img'); img.src = item.logo; img.alt = item.underlying || 'Ação'; img.loading = 'lazy'; logoCell.appendChild(img);
      }
      const asset = document.createElement('span'); asset.textContent = item.underlying || '—'; logoCell.appendChild(asset); tr.appendChild(logoCell);
      [item.option_code, date(item.open_date), date(item.close_date), item.modality, money(item.taxable_base), money(item.tax)].forEach(value => {
        const td = document.createElement('td'); td.textContent = value || '—'; tr.appendChild(td);
      });
      return tr;
    }));
    const baseTotal = rows.reduce((sum, item) => sum + Number(item.taxable_base || 0), 0);
    const grossTaxTotal = rows.reduce((sum, item) => sum + Number(item.tax || 0), 0);
    const darfTotal = Number(trigger.dataset.darfTotal || 0);
    totals.replaceChildren();
    if (rows.length) {
      const tr = document.createElement('tr');
      const label = document.createElement('th'); label.colSpan = 5; label.textContent = darfTotal > 0 ? `Total da DARF: ${money(darfTotal)}` : 'Totais do período'; tr.appendChild(label);
      [money(baseTotal), money(grossTaxTotal)].forEach(value => { const th = document.createElement('th'); th.textContent = value; tr.appendChild(th); });
      totals.appendChild(tr);
    }
    empty.hidden = rows.length > 0;
    dialog.showModal();
  });
  dialog.querySelector('[data-close-dialog]').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
})();
