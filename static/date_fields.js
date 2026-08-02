(function () {
  'use strict';
  const valueDescriptor = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
  const nativeGetValue = valueDescriptor.get;
  const nativeSetValue = valueDescriptor.set;
  const digits = (value, length) => String(value || '').replace(/\D/g, '').slice(0, length);
  const isRealDate = (day, month, year) => {
    const date = new Date(Date.UTC(year, month - 1, day));
    return date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day;
  };

  function enhanceDateField(input) {
    if (input.dataset.segmentedDate === 'true' || input.type !== 'date') return;
    input.dataset.segmentedDate = 'true';
    const wrapper = document.createElement('span');
    wrapper.className = 'segmented-date';
    wrapper.setAttribute('role', 'group');
    wrapper.setAttribute('aria-label', input.getAttribute('aria-label') || 'Data no formato dia, mês e ano');
    const parts = [
      { key: 'day', placeholder: 'DD', max: 2, label: 'Dia' },
      { key: 'month', placeholder: 'MM', max: 2, label: 'Mês' },
      { key: 'year', placeholder: 'AAAA', max: 4, label: 'Ano' }
    ].map((part, index) => {
      const field = document.createElement('input');
      field.type = 'text';
      field.inputMode = 'numeric';
      field.autocomplete = 'off';
      field.maxLength = part.max;
      field.placeholder = part.placeholder;
      field.className = `segmented-date__${part.key}`;
      field.setAttribute('aria-label', part.label);
      field.dataset.datePart = part.key;
      field.disabled = input.disabled;
      field.readOnly = input.readOnly;
      wrapper.appendChild(field);
      if (index < 2) {
        const separator = document.createElement('span');
        separator.className = 'segmented-date__separator';
        separator.textContent = '/';
        separator.setAttribute('aria-hidden', 'true');
        wrapper.appendChild(separator);
      }
      return field;
    });
    const [dayField, monthField, yearField] = parts;
    input.classList.add('segmented-date__original');
    input.insertAdjacentElement('afterend', wrapper);

    function syncFromOriginal() {
      const match = nativeGetValue.call(input).match(/^(\d{4})-(\d{2})-(\d{2})$/);
      input.setCustomValidity('');
      wrapper.classList.remove('segmented-date--invalid');
      if (!match) {
        dayField.value = monthField.value = yearField.value = '';
        return;
      }
      yearField.value = match[1];
      monthField.value = match[2];
      dayField.value = match[3];
    }

    function syncToOriginal(emitEvent) {
      const day = Number(dayField.value);
      const month = Number(monthField.value);
      const year = Number(yearField.value);
      const anyPart = Boolean(dayField.value || monthField.value || yearField.value);
      const complete = dayField.value.length === 2 && monthField.value.length === 2 && yearField.value.length === 4;
      const valid = complete && isRealDate(day, month, year);
      nativeSetValue.call(input, valid ? `${String(year).padStart(4, '0')}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}` : '');
      input.setCustomValidity(anyPart && !complete ? 'Complete a data com dia, mês e ano.' : complete && !valid ? 'Informe uma data válida.' : '');
      wrapper.classList.toggle('segmented-date--invalid', anyPart && (!complete || !valid));
      if (emitEvent) input.dispatchEvent(new Event('input', { bubbles: true }));
    }

    Object.defineProperty(input, 'value', {
      configurable: true,
      enumerable: valueDescriptor.enumerable,
      get() { return nativeGetValue.call(input); },
      set(value) { nativeSetValue.call(input, value); syncFromOriginal(); }
    });

    parts.forEach((field, index) => {
      field.addEventListener('input', () => {
        field.value = digits(field.value, field.maxLength);
        syncToOriginal(true);
        if (field.value.length === field.maxLength && index < parts.length - 1) {
          parts[index + 1].focus();
          parts[index + 1].select();
        } else if (field.value.length === field.maxLength && index === parts.length - 1) {
          const focusable = Array.from(document.querySelectorAll('button, input:not([type="hidden"]), select, textarea, a[href]'));
          const currentIndex = focusable.indexOf(field);
          const next = focusable.slice(currentIndex + 1).find(element => !element.disabled && element.offsetParent !== null);
          if (next) next.focus();
        }
      });
      field.addEventListener('keydown', event => {
        if (event.key === 'Backspace' && !field.value && index > 0) {
          event.preventDefault();
          parts[index - 1].focus();
          parts[index - 1].setSelectionRange(parts[index - 1].value.length, parts[index - 1].value.length);
        }
        if (event.key === 'ArrowLeft' && field.selectionStart === 0 && index > 0) parts[index - 1].focus();
        if (event.key === 'ArrowRight' && field.selectionStart === field.value.length && index < parts.length - 1) parts[index + 1].focus();
      });
      field.addEventListener('paste', event => {
        const match = event.clipboardData.getData('text').match(/^(\d{1,2})[\/-](\d{1,2})[\/-](\d{4})$/);
        if (!match) return;
        event.preventDefault();
        dayField.value = match[1].padStart(2, '0');
        monthField.value = match[2].padStart(2, '0');
        yearField.value = match[3];
        syncToOriginal(true);
        yearField.focus();
      });
      field.addEventListener('change', () => input.dispatchEvent(new Event('change', { bubbles: true })));
    });
    input.addEventListener('invalid', event => {
      event.preventDefault();
      wrapper.classList.add('segmented-date--invalid');
      (dayField.value.length < 2 ? dayField : monthField.value.length < 2 ? monthField : yearField).focus();
    });
    input.addEventListener('focus', () => dayField.focus());
    input.form?.addEventListener('reset', () => setTimeout(syncFromOriginal));
    syncFromOriginal();
  }

  function enhanceAll(root) {
    if (root.matches?.('input[type="date"]')) enhanceDateField(root);
    root.querySelectorAll?.('input[type="date"]').forEach(enhanceDateField);
  }
  window.segmentedDates = { enhance: enhanceDateField, enhanceAll };
  enhanceAll(document);
  new MutationObserver(records => records.forEach(record => record.addedNodes.forEach(node => {
    if (node.nodeType === Node.ELEMENT_NODE) enhanceAll(node);
  }))).observe(document.body, { childList: true, subtree: true });
})();
