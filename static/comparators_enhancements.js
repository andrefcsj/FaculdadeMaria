(() => {
  const setup = ({ modalId, formId, assetId, detailsId, previewId, prefix }) => {
    const modal = document.getElementById(modalId);
    const form = document.getElementById(formId);
    const asset = document.getElementById(assetId);
    const details = document.getElementById(detailsId);
    if (!modal || !form || !asset || !details) return;

    const upperCase = input => {
      if (input.type === 'date' || input.type === 'number') return;
      const position = input.selectionStart;
      input.value = input.value.toUpperCase();
      if (position !== null) input.setSelectionRange(position, position);
    };
    modal.addEventListener('input', event => {
      if (event.target.matches('input')) upperCase(event.target);
    });
    modal.addEventListener('keydown', event => {
      if (event.key !== 'Enter' || event.target.tagName !== 'INPUT') return;
      event.preventDefault();
      const fields = [...form.querySelectorAll('input:not([type="hidden"]):not([disabled])')]
        .filter(field => field.offsetParent !== null);
      const index = fields.indexOf(event.target);
      const next = fields[index + 1];
      if (next) next.focus();
      else form.querySelector('button[type="submit"]')?.focus();
    });

    let preview = document.getElementById(previewId);
    if (!preview) {
      preview = document.createElement('div');
      preview.id = previewId;
      preview.className = `${prefix}-asset-preview`;
      preview.innerHTML = '<img alt=""><span></span>';
      asset.closest('.ccx-grid')?.insertAdjacentElement('afterend', preview);
    }
    const image = preview.querySelector('img');
    const label = preview.querySelector('span');
    const updateLogo = () => {
      const ticker = asset.value.trim().toUpperCase().replace(/\.SA$/, '');
      asset.value = ticker;
      if (!/^[A-Z]{4}\d{1,2}$/.test(ticker)) { preview.hidden = true; return; }
      label.textContent = ticker;
      image.alt = `Logo de ${ticker}`;
      image.src = `https://raw.githubusercontent.com/thefintz/icones-b3/main/icones/${encodeURIComponent(ticker)}.png`;
      preview.hidden = false;
    };
    image.addEventListener('error', () => { preview.hidden = true; });
    asset.addEventListener('input', updateLogo);

    let timer;
    form.addEventListener('input', event => {
      if (details.hidden || event.target === asset) return;
      clearTimeout(timer);
      modal.querySelector('.ccx-dialog')?.classList.add('ccx-is-updating');
      timer = setTimeout(() => {
        form.requestSubmit();
        modal.querySelector('.ccx-dialog')?.classList.remove('ccx-is-updating');
      }, 550);
    });
  };
  setup({ modalId: 'coveredCallComparatorModal', formId: 'ccxForm', assetId: 'ccxAsset', detailsId: 'ccxDetails', previewId: 'ccxAssetPreview', prefix: 'ccx' });
  setup({ modalId: 'putComparatorModal', formId: 'pcxForm', assetId: 'pcxAsset', detailsId: 'pcxDetails', previewId: 'pcxAssetPreview', prefix: 'pcx' });
})();
