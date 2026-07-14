document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('newBrokerageNote');
  const result = document.getElementById('brokerageImportResult');
  const footer = document.getElementById('newOperationFooterHint');
  const operationForm = document.getElementById('newOperationForm');
  if (!input || !result || !operationForm) return;

  let note = null;
  let selectedTrade = null;
  let selectedIndex = -1;
  let confirmedClosureId = null;
  const processedTrades = new Set();
  const q = id => document.getElementById(id);
  const brl = value => new Intl.NumberFormat('pt-BR', {style: 'currency', currency: 'BRL'}).format(Number(value) || 0);

  function tradeLabel(trade) {
    const done = processedTrades.has(Number(trade.trade_index)) ? '✓ ' : '';
    return `${done}${trade.option_code} • ${trade.side} • ${trade.quantity} opções • ${brl(trade.gross_value)}`;
  }

  function refreshOptions() {
    const select = q('brokerageTradeSelect');
    if (!select || !note) return;
    [...select.options].forEach((option, index) => {
      const trade = note.trades[index];
      option.textContent = tradeLabel(trade);
      option.disabled = processedTrades.has(Number(trade.trade_index));
    });
    select.value = String(selectedIndex);
  }

  function updateFooter(prefix = '') {
    if (!note || !selectedTrade) return;
    const candidate = selectedTrade.closure_candidate;
    const remaining = note.trades.length - processedTrades.size;
    const progress = note.trades.length > 1 ? ` Negociação ${processedTrades.size + 1} de ${note.trades.length}.` : '';
    const message = confirmedClosureId
      ? `Encerramento confirmado para ${selectedTrade.option_code}. Ao salvar, a posição será fechada.`
      : candidate
        ? `Possível encerramento ${candidate.match_type}. Confira as quantidades antes de continuar.`
        : `Confira strike e vencimento de ${selectedTrade.option_code} antes de salvar.`;
    footer.textContent = `${prefix}${progress} ${message}${remaining > 1 ? ' As demais negociações serão apresentadas em seguida.' : ''}`.trim();
  }

  function applyTrade(index, prefix = '') {
    selectedIndex = Number(index);
    selectedTrade = note?.trades[selectedIndex] || null;
    confirmedClosureId = null;
    if (!selectedTrade) return;

    // Dados estruturais pertencem a cada código. Limpá-los evita que o strike,
    // vencimento ou cotação da negociação anterior permaneçam na tela.
    q('newUnderlying').value = '';
    q('newStrike').value = '';
    q('newExpiry').value = '';
    q('newSpot').value = '';
    q('newOptionHint').textContent = 'Buscando os dados desta opção...';

    q('newOptionCode').value = selectedTrade.option_code;
    q('newContracts').value = selectedTrade.contracts;
    q('newPremium').value = brl(selectedTrade.unit_price);
    q('newCosts').value = brl(selectedTrade.allocated_costs);
    q('newIrrf').value = brl(selectedTrade.allocated_irrf);

    const strategy = operationForm.querySelector(`input[name="Estrategia"][value="${selectedTrade.side}"]`);
    if (strategy) {
      strategy.checked = true;
      strategy.dispatchEvent(new Event('change', {bubbles: true}));
    }
    const typeValue = selectedTrade.market.toLowerCase().includes('venda') ? 'PUT' : 'CALL';
    const type = operationForm.querySelector(`input[name="Tipo"][value="${typeValue}"]`);
    if (type) type.checked = true;

    // Atualiza o resumo sem disparar a consulta genérica que usa o prêmio da
    // posição aberta. O preço real da nota deve permanecer no campo.
    q('newOptionCode').dispatchEvent(new Event('change', {bubbles: true}));
    q('newPremium').dispatchEvent(new Event('change', {bubbles: true}));
    document.dispatchEvent(new CustomEvent('brokerage-trade-applied', {
      detail: {optionCode: selectedTrade.option_code, tradeIndex: selectedTrade.trade_index, tradeDate: note.trade_date}
    }));

    const candidate = selectedTrade.closure_candidate;
    if (candidate?.match_type === 'total') {
      const accepted = confirm(`Encerramento identificado: a compra de ${candidate.note_quantity} opções ${candidate.option_code} corresponde à posição aberta. Deseja encerrar esta operação?`);
      if (accepted) confirmedClosureId = candidate.operation_id;
    }
    refreshOptions();
    updateFooter(prefix);
    const saveButton = q('newOperationSave');
    if (saveButton && note.trades.length > 1) {
      saveButton.textContent = `Salvar negociação ${processedTrades.size + 1} de ${note.trades.length}`;
    }
  }

  input.addEventListener('change', async () => {
    const file = input.files?.[0];
    if (!file) return;
    result.hidden = false;
    result.innerHTML = '<strong>Lendo nota BTG/Necton...</strong>';
    const body = new FormData();
    body.append('brokerage_note', file);
    try {
      const response = await fetch('/api/notas-corretagem/analisar', {method: 'POST', body});
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error || 'Não foi possível ler a nota.');
      note = data.note;
      processedTrades.clear();
      const options = note.trades.map((trade, index) => `<option value="${index}">${tradeLabel(trade)}</option>`).join('');
      const multipleHint = note.trades.length > 1
        ? `<small>A nota possui ${note.trades.length} negociações. Salve cada uma; a próxima será carregada automaticamente.</small>`
        : '<small>O PDF não será armazenado. Confira os campos antes de cadastrar.</small>';
      result.innerHTML = `<strong>Nota ${note.note_number} reconhecida</strong><br>Crédito/débito líquido: ${brl(note.net_cash)} • Custos efetivos: ${brl(note.operational_costs)}<select id="brokerageTradeSelect" aria-label="Selecione a operação da nota">${options}</select>${multipleHint}`;
      q('brokerageTradeSelect').addEventListener('change', event => applyTrade(event.target.value));
      applyTrade(0);
    } catch (error) {
      note = null;
      selectedTrade = null;
      result.innerHTML = `<strong>Não foi possível importar:</strong> ${error.message}`;
    }
  });

  window.brokerageNoteImport = {
    preparePayload(payload) {
      if (!note || !selectedTrade) return payload;
      const prepared = {
        ...payload,
        Data_abertura: note.trade_date,
        Nota_corretagem: {...note, trade: selectedTrade}
      };
      if (confirmedClosureId) prepared.Encerrar_operacao_id = confirmedClosureId;
      return prepared;
    },
    handleSaved() {
      if (!note || !selectedTrade) return false;
      processedTrades.add(Number(selectedTrade.trade_index));
      const nextIndex = note.trades.findIndex(trade => !processedTrades.has(Number(trade.trade_index)));
      if (nextIndex < 0) return false;
      applyTrade(nextIndex, `${selectedTrade.option_code} foi salva com sucesso.`);
      return true;
    },
    buttonLabel() {
      if (!note || note.trades.length < 2) return '＋ Cadastrar operação';
      return `Salvar negociação ${processedTrades.size + 1} de ${note.trades.length}`;
    },
    finish() {
      note = null;
      selectedTrade = null;
      selectedIndex = -1;
      confirmedClosureId = null;
      processedTrades.clear();
      input.value = '';
      result.hidden = true;
      result.innerHTML = '';
      footer.textContent = 'A operação será adicionada à carteira em aberto.';
    }
  };
});
