document.addEventListener('DOMContentLoaded', () => {
  const search = document.getElementById('buscaAtivo');
  const modal = document.getElementById('editOperationModal');
  const form = document.getElementById('editOperationForm');
  const errorBox = document.getElementById('editError');
  const saveButton = document.getElementById('saveOperationButton');

  const fields = {
    id: document.getElementById('editId'),
    underlying: document.getElementById('editUnderlying'),
    option: document.getElementById('editAtivo'),
    strike: document.getElementById('editStrike'),
    contracts: document.getElementById('editContratos'),
    premium: document.getElementById('editPremio'),
    expiry: document.getElementById('editVencimento'),
    spot: document.getElementById('editCotacao'),
    status: document.getElementById('editStatus'),
    costs: document.getElementById('editCustos'),
    irrf: document.getElementById('editIrrf'),
  };

  const summaryCode = document.getElementById('summaryCode');
  const summaryDetails = document.getElementById('summaryDetails');
  const summaryPremium = document.getElementById('summaryPremium');
  const premiumTotal = document.getElementById('premiumTotal');

  const parseNumber = (value) => {
    const text = String(value ?? '').replace('R$', '').replace(/\s/g, '');
    if (!text) return 0;
    if (text.includes(',') && text.includes('.')) {
      return Number(text.replace(/\./g, '').replace(',', '.')) || 0;
    }
    return Number(text.replace(',', '.')) || 0;
  };

  const formatMoney = (value) => new Intl.NumberFormat('pt-BR', {
    style: 'currency', currency: 'BRL'
  }).format(Number.isFinite(value) ? value : 0);

  const toIsoDate = (value) => {
    const text = String(value ?? '').trim();
    if (/^\d{4}-\d{2}-\d{2}$/.test(text)) return text;
    const match = text.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
    return match ? `${match[3]}-${match[2]}-${match[1]}` : text;
  };

  const inferUnderlying = (optionCode) => {
    const code = String(optionCode ?? '').trim().toUpperCase();
    const match = code.match(/^([A-Z]{4})(\d)/);
    return match ? `${match[1]}${match[2]}` : code.slice(0, 5);
  };

  const setChecked = (name, value, fallback) => {
    const normalized = String(value || fallback).toUpperCase();
    const radios = form.querySelectorAll(`input[name="${name}"]`);
    radios.forEach((radio) => {
      radio.checked = radio.value.toUpperCase() === normalized;
    });
    if (![...radios].some((radio) => radio.checked) && radios[0]) radios[0].checked = true;
  };

  const updateSummary = () => {
    const optionCode = fields.option?.value.trim().toUpperCase() || 'Opção';
    const contracts = Math.max(parseNumber(fields.contracts?.value), 0);
    const premium = Math.max(parseNumber(fields.premium?.value), 0);
    const strike = Math.max(parseNumber(fields.strike?.value), 0);
    const quantity = contracts * 100;
    const total = premium * quantity;
    if (fields.underlying) fields.underlying.value = inferUnderlying(optionCode);
    if (summaryCode) summaryCode.textContent = optionCode;
    if (summaryDetails) summaryDetails.textContent = `${quantity || 0} ações • Strike ${formatMoney(strike)}`;
    if (summaryPremium) summaryPremium.textContent = formatMoney(total);
    if (premiumTotal) premiumTotal.textContent = `Total estimado: ${formatMoney(total)}`;
  };

  const showError = (message) => {
    if (!errorBox) return;
    errorBox.textContent = message;
    errorBox.style.display = 'block';
  };

  const clearError = () => {
    if (!errorBox) return;
    errorBox.textContent = '';
    errorBox.style.display = 'none';
  };

  const openModal = () => {
    if (!modal) return;
    modal.hidden = false;
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    window.setTimeout(() => fields.option?.focus(), 50);
  };

  const closeModal = () => {
    if (!modal) return;
    modal.hidden = true;
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    clearError();
  };

  const loadOperation = async (operationId) => {
    clearError();
    if (saveButton) saveButton.disabled = true;
    try {
      const response = await fetch(`/api/operacoes/${encodeURIComponent(operationId)}`, {
        headers: { Accept: 'application/json' }
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.error || 'Não foi possível carregar a operação.');
      const operation = payload.operation;
      fields.id.value = operation.ID;
      fields.option.value = operation.Ativo || '';
      fields.strike.value = operation.Strike || '0';
      fields.contracts.value = operation.Contratos || '1';
      fields.premium.value = operation.Premio_opcao || '0';
      fields.expiry.value = toIsoDate(operation.Vencimento || '');
      fields.spot.value = operation.Cotacao_atual || '0';
      fields.status.value = operation.Status || 'Aberta';
      fields.costs.value = operation.Custos || '0';
      fields.irrf.value = operation.IRRF || '0';
      setChecked('Tipo', operation.Tipo, 'PUT');
      setChecked('Estrategia', operation.Estrategia, 'Venda');
      updateSummary();
      openModal();
    } catch (error) {
      window.alert(error.message || 'Não foi possível abrir a edição.');
    } finally {
      if (saveButton) saveButton.disabled = false;
    }
  };

  if (search) {
    search.addEventListener('input', () => {
      const term = search.value.toLowerCase();
      document.querySelectorAll('#tabelaOperacoes tbody tr').forEach((row) => {
        row.style.display = row.innerText.toLowerCase().includes(term) ? '' : 'none';
      });
    });
  }

  document.addEventListener('click', (event) => {
    const editButton = event.target.closest('[data-edit-id]');
    if (editButton) {
      event.preventDefault();
      loadOperation(editButton.dataset.editId);
      return;
    }

    if (event.target.closest('[data-modal-close]')) {
      closeModal();
      return;
    }

    const deleteButton = event.target.closest('.btn-action.delete');
    if (deleteButton && !window.confirm('Tem certeza que deseja excluir esta operação?')) {
      event.preventDefault();
      event.stopPropagation();
    }
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && modal && !modal.hidden) closeModal();
  });

  ['input', 'change'].forEach((eventName) => {
    ['editAtivo', 'editStrike', 'editContratos', 'editPremio'].forEach((id) => {
      document.getElementById(id)?.addEventListener(eventName, updateSummary);
    });
  });

  form?.addEventListener('submit', async (event) => {
    event.preventDefault();
    clearError();
    if (!form.reportValidity()) return;

    const operationId = fields.id.value;
    const selectedType = form.querySelector('input[name="Tipo"]:checked');
    const selectedStrategy = form.querySelector('input[name="Estrategia"]:checked');
    const payload = {
      Ativo: fields.option.value.trim().toUpperCase(),
      Tipo: selectedType?.value || 'PUT',
      Estrategia: selectedStrategy?.value || 'Venda',
      Status: fields.status.value,
      Contratos: fields.contracts.value,
      Strike: fields.strike.value,
      Premio_opcao: fields.premium.value,
      Custos: fields.costs.value,
      IRRF: fields.irrf.value,
      Vencimento: fields.expiry.value,
      Cotacao_atual: fields.spot.value,
    };

    if (saveButton) {
      saveButton.disabled = true;
      saveButton.textContent = 'Salvando...';
    }
    try {
      const response = await fetch(`/api/operacoes/${encodeURIComponent(operationId)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error(result.error || 'Não foi possível salvar a operação.');
      closeModal();
      window.location.reload();
    } catch (error) {
      showError(error.message || 'Erro inesperado ao salvar.');
    } finally {
      if (saveButton) {
        saveButton.disabled = false;
        saveButton.textContent = 'Salvar alterações';
      }
    }
  });
});
