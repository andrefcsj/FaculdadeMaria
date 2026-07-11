document.addEventListener('DOMContentLoaded',()=>{
  const busca=document.getElementById('buscaAtivo');
  if(busca){
    busca.addEventListener('input',()=>{
      const termo=busca.value.toLowerCase();
      document.querySelectorAll('#tabelaOperacoes tbody tr').forEach(linha=>{
        linha.style.display=linha.innerText.toLowerCase().includes(termo)?'':'none';
      });
    });
  }

  const modal=document.getElementById('closeOperationModal');
  const form=document.getElementById('closeOperationForm');
  if(!modal || !form) return;

  const methodInput=document.getElementById('closeMethod');
  const dateInput=document.getElementById('closeDate');
  const repurchase=document.getElementById('repurchaseValue');
  const repurchaseField=document.getElementById('repurchaseField');
  const resultOutput=document.getElementById('closeResult');
  const errorBox=document.getElementById('closeError');
  const hint=document.getElementById('closeMethodHint');
  const expiredMethod=document.getElementById('expiredMethod');
  let operation={};

  const brl=value=>Number(value||0).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
  const today=()=>new Date().toISOString().slice(0,10);
  const hints={
    recompra:'↻ Posição zerada com lucro/prejuízo na recompra.',
    exercida:'ϟ Exercício faz parte da estratégia; o prêmio recebido é preservado.',
    cancelada:'⊗ Registro encerrado por cancelamento ou correção operacional.',
    virou_po:'✧ Opção expirada sem valor; prêmio integral preservado.'
  };

  function calculateResult(){
    const method=methodInput.value;
    const premium=Number(operation.premiumTotal||0);
    const buyback=Number(repurchase.value||0)*Number(operation.contracts||0)*Number(operation.contractSize||0);
    const result=method==='recompra'?premium-buyback:method==='cancelada'?0:premium;
    resultOutput.value=brl(result);
    resultOutput.textContent=brl(result);
    resultOutput.classList.toggle('close-result--positive',result>0);
    resultOutput.classList.toggle('close-result--negative',result<0);
  }

  function updateExpiredAvailability(){
    const allowed=!operation.expiry || dateInput.value>=operation.expiry;
    expiredMethod.classList.toggle('is-disabled',!allowed);
    expiredMethod.disabled=!allowed;
    if(!allowed && methodInput.value==='virou_po') selectMethod('recompra');
  }

  function selectMethod(method){
    const selected=form.querySelector(`[data-method="${method}"]`);
    if(!selected || selected.disabled) return;
    methodInput.value=method;
    form.querySelectorAll('.close-method').forEach(button=>button.classList.toggle('active',button===selected));
    repurchaseField.style.opacity=method==='recompra'?'1':'.5';
    repurchase.disabled=method!=='recompra';
    repurchase.required=method==='recompra';
    hint.textContent=hints[method];
    errorBox.hidden=true;
    calculateResult();
  }

  function openModal(button){
    operation={
      closeUrl:button.dataset.closeUrl,
      option:button.dataset.option,
      ticker:button.dataset.ticker,
      type:button.dataset.type,
      strategy:button.dataset.strategy,
      strike:Number(button.dataset.strike||0),
      expiry:button.dataset.expiry,
      expiryLabel:button.dataset.expiryLabel,
      contracts:Number(button.dataset.contracts||0),
      contractSize:Number(button.dataset.contractSize||100),
      premiumTotal:Number(button.dataset.premiumTotal||0)
    };
    form.action=operation.closeUrl;
    document.getElementById('closeAssetLetter').textContent=(operation.ticker||operation.option||'?').slice(0,1);
    document.getElementById('closeOperationDescription').textContent=`${operation.option} · ${operation.strategy} ${operation.type} · strike ${brl(operation.strike)} · venc. ${operation.expiryLabel||'—'}`;
    dateInput.value=today();
    repurchase.value='0.00';
    modal.hidden=false;
    modal.setAttribute('aria-hidden','false');
    document.body.classList.add('close-modal-open');
    updateExpiredAvailability();
    selectMethod('recompra');
    setTimeout(()=>repurchase.focus(),80);
  }

  function closeModal(){
    modal.hidden=true;
    modal.setAttribute('aria-hidden','true');
    document.body.classList.remove('close-modal-open');
    errorBox.hidden=true;
  }

  document.addEventListener('click',event=>{
    const closeButton=event.target.closest('.js-open-close-modal');
    if(closeButton){event.preventDefault();openModal(closeButton);return;}
    if(event.target.closest('[data-close-modal]')){event.preventDefault();closeModal();return;}
    const methodButton=event.target.closest('.close-method');
    if(methodButton){selectMethod(methodButton.dataset.method);return;}
    const deleteButton=event.target.closest('.btn-action.delete');
    if(deleteButton && !confirm('Tem certeza que deseja excluir esta operação?')){event.preventDefault();event.stopPropagation();}
  });
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!modal.hidden)closeModal();});
  repurchase.addEventListener('input',calculateResult);
  dateInput.addEventListener('change',updateExpiredAvailability);

  form.addEventListener('submit',async event=>{
    event.preventDefault();
    errorBox.hidden=true;
    const confirmButton=form.querySelector('.close-confirm');
    confirmButton.disabled=true;
    confirmButton.textContent='Encerrando...';
    try{
      const response=await fetch(form.action,{method:'POST',body:new FormData(form),headers:{'X-Requested-With':'XMLHttpRequest'}});
      const data=await response.json();
      if(!response.ok||!data.ok) throw new Error(data.message||'Não foi possível encerrar a operação.');
      window.location.assign(data.redirect||'/operacoes-abertas');
    }catch(error){
      errorBox.textContent=error.message;
      errorBox.hidden=false;
      confirmButton.disabled=false;
      confirmButton.textContent='✓ Confirmar encerramento';
    }
  });
});
