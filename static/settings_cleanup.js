document.addEventListener('DOMContentLoaded',()=>{
  const page=document.querySelector('.settings-page'),modal=document.getElementById('cleanupModal');
  if(!page||!modal)return;
  const q=id=>document.getElementById(id),preview=q('cleanupPreview'),expected=q('cleanupExpected'),pin=q('cleanupPin'),confirmation=q('cleanupConfirmation'),error=q('cleanupError'),execute=q('cleanupExecute');
  let requestPayload=null;
  document.addEventListener('click',event=>{
    const button=event.target.closest('[data-cleanup-scope]');
    if(button)open(button.dataset.cleanupScope);
    if(event.target.closest('[data-cleanup-close]'))close();
  });
  function close(){modal.hidden=true;document.body.style.overflow='';error.hidden=true;pin.value='';confirmation.value=''}
  async function open(scope){
    let period='';if(scope==='month')period=q('cleanupMonth').value;if(scope==='year')period=q('cleanupYear').value;
    if(scope!=='all'&&!period){alert('Selecione o período.');return}
    requestPayload={scope,period};modal.hidden=false;document.body.style.overflow='hidden';preview.textContent='Calculando registros afetados...';
    try{
      const response=await fetch('/api/configuracoes/limpeza/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(requestPayload)}),data=await response.json();
      if(!response.ok||!data.ok)throw new Error(data.error||'Falha na prévia.');
      expected.textContent=data.confirmation;
      preview.innerHTML=`<strong>${data.preview.operations} operação(ões)</strong><br>${data.preview.notes} nota(s) • ${data.preview.closures} encerramento(s) • ${data.preview.cash_events} aporte(s)/retirada(s) • ${data.preview.paid_darfs} DARF(s) • ${data.preview.legacy} legado(s)`;
      if(!data.enabled)preview.innerHTML+='<br><b>A limpeza está bloqueada até configurar ADMIN_RESET_PIN no Render.</b>';
    }catch(err){error.textContent=err.message;error.hidden=false}
  }
  execute.addEventListener('click',async()=>{
    if(!requestPayload)return;error.hidden=true;execute.disabled=true;execute.textContent='Excluindo...';
    try{
      const response=await fetch('/api/configuracoes/limpeza/executar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...requestPayload,pin:pin.value,confirmation:confirmation.value})}),data=await response.json();
      if(!response.ok||!data.ok)throw new Error(data.error||'Não foi possível excluir.');window.location.assign('/?limpeza=concluida');
    }catch(err){error.textContent=err.message;error.hidden=false;execute.disabled=false;execute.textContent='Excluir dados selecionados'}
  });
});
