document.addEventListener('DOMContentLoaded',()=>{
  const modal=document.getElementById('equityModal'),form=document.getElementById('equityForm');
  const asset=document.getElementById('equityAsset'),quantity=document.getElementById('equityQuantity');
  const average=document.getElementById('equityAverage'),date=document.getElementById('equityDate');
  const saleField=document.getElementById('equitySalePriceField'),salePrice=document.getElementById('equitySalePrice');
  const title=document.getElementById('equityModalTitle'),hint=document.getElementById('equityModalHint');
  const error=document.getElementById('equityError'),submit=document.getElementById('equitySubmit');
  let mode='add',currentAsset='';
  const today=()=>new Date().toISOString().slice(0,10);
  const rowData=row=>({asset:row.dataset.asset,quantity:row.dataset.quantity,average:row.dataset.average,date:row.dataset.date,available:row.dataset.available});
  function open(nextMode,data={}){
    mode=nextMode;currentAsset=data.asset||'';error.hidden=true;form.reset();date.value=data.date||today();
    asset.value=data.asset||'';quantity.value=data.quantity||'';average.value=data.average||'';
    asset.readOnly=mode!=='add';saleField.hidden=mode!=='sell';saleField.style.display=mode==='sell'?'flex':'none';average.closest('label').hidden=mode==='sell';average.closest('label').style.display=mode==='sell'?'none':'flex';
    title.textContent=mode==='add'?'Adicionar ação':mode==='edit'?'Editar posição':'Registrar venda';
    hint.textContent=mode==='sell'?`Disponíveis para venda: ${data.available||0}`:'Os totais da carteira serão recalculados automaticamente.';
    submit.textContent=mode==='sell'?'Confirmar venda':'Salvar';modal.hidden=false;
  }
  const close=()=>{modal.hidden=true};
  document.querySelector('[data-equity-add]')?.addEventListener('click',()=>open('add'));
  document.querySelectorAll('[data-equity-close]').forEach(button=>button.addEventListener('click',close));
  document.addEventListener('click',async event=>{
    const row=event.target.closest('[data-equity-row]');if(!row)return;const data=rowData(row);
    if(event.target.closest('[data-equity-edit]'))open('edit',data);
    if(event.target.closest('[data-equity-sell]'))open('sell',{...data,quantity:data.available});
    if(event.target.closest('[data-equity-delete]')){
      if(!confirm(`Excluir ${data.asset} da carteira? Esta ação não pode ser desfeita.`))return;
      const response=await fetch(`/api/carteira-acoes/${encodeURIComponent(data.asset)}`,{method:'DELETE'}),payload=await response.json();
      if(!response.ok||!payload.ok)return alert(payload.error||'Não foi possível excluir.');location.reload();
    }
  });
  form?.addEventListener('submit',async event=>{
    event.preventDefault();error.hidden=true;
    const base={asset:asset.value.trim().toUpperCase(),quantity:Number(quantity.value),average_price:average.value,acquisition_date:date.value};
    let url='/api/carteira-acoes/manual',method='POST',payload=base;
    if(mode==='edit'){url=`/api/carteira-acoes/${encodeURIComponent(currentAsset)}`;method='PUT'}
    if(mode==='sell'){url=`/api/carteira-acoes/${encodeURIComponent(currentAsset)}/vender`;payload={quantity:Number(quantity.value),sale_price:salePrice.value,sale_date:date.value}}
    try{
      const response=await fetch(url,{method,headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}),data=await response.json();
      if(!response.ok||!data.ok)throw new Error(data.error||'Não foi possível salvar.');location.reload();
    }catch(exc){error.textContent=exc.message;error.hidden=false}
  });
  const input=document.getElementById('equityNoteFile'),status=document.getElementById('equityImportStatus');
  const noteModal=document.getElementById('equityNoteModal'),noteSummary=document.getElementById('equityNoteSummary'),noteConfirm=document.getElementById('equityNoteConfirm');
  let pendingNoteFile=null;
  const brl=value=>new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(Number(value)||0);
  const dateBr=value=>{const parts=String(value||'').split('-');return parts.length===3?`${parts[2]}/${parts[1]}/${parts[0]}`:value};
  const closeNote=()=>{noteModal.hidden=true;pendingNoteFile=null;input.value=''};
  document.querySelectorAll('[data-equity-note-close]').forEach(button=>button.addEventListener('click',closeNote));
  input?.addEventListener('change',async()=>{
    if(!input.files?.[0])return;pendingNoteFile=input.files[0];status.hidden=false;status.classList.remove('error');status.textContent='Lendo a nota para conferência...';
    const body=new FormData();body.append('brokerage_note',pendingNoteFile);
    try{
      const response=await fetch('/api/notas-corretagem/analisar',{method:'POST',body}),data=await response.json();if(!response.ok||!data.ok)throw new Error(data.error||'Não foi possível analisar.');
      const note=data.note,trades=note.trades.filter(trade=>['equity_purchase','equity_sale'].includes(trade.event_type));if(!trades.length)throw new Error('A nota não possui compra ou venda de ações reconhecida.');
      noteSummary.innerHTML=`<div class="equity-note-overview"><div><small>Nota</small><strong>${note.note_number}</strong></div><div><small>Pregão</small><strong>${dateBr(note.trade_date)}</strong></div><div><small>Líquido</small><strong>${note.cash_direction==='C'?'Crédito':'Débito'} ${brl(note.net_cash)}</strong></div><div><small>Custos + IRRF</small><strong>${brl(Number(note.operational_costs)+Number(note.irrf))}</strong></div></div><div class="equity-note-trades">${trades.map(trade=>`<div class="equity-note-trade"><div><small>Operação</small><strong>${trade.side} de ${trade.underlying_asset}</strong></div><div><small>Quantidade</small><strong>${trade.quantity}</strong></div><div><small>Preço unitário</small><strong>${brl(trade.unit_price)}</strong></div><div><small>Valor bruto</small><strong>${brl(trade.gross_value)}</strong></div></div>`).join('')}</div><p class="equity-note-warning">Ao confirmar, a carteira e o caixa serão recalculados. Vendas também aparecerão em Operações Fechadas e, para ações comuns, entrarão na previsão de DARF.</p>`;
      status.hidden=true;noteModal.hidden=false;
    }catch(exc){status.textContent=exc.message;status.classList.add('error');pendingNoteFile=null;input.value=''}
  });
  noteConfirm?.addEventListener('click',async()=>{
    if(!pendingNoteFile)return;noteConfirm.disabled=true;noteConfirm.textContent='Importando e recalculando...';const body=new FormData();body.append('brokerage_note',pendingNoteFile);
    try{const response=await fetch('/api/carteira-acoes/importar-nota',{method:'POST',body}),data=await response.json();if(!response.ok||!data.ok)throw new Error(data.error||'Não foi possível importar.');status.hidden=false;status.classList.remove('error');status.textContent=data.message;location.reload()}
    catch(exc){noteModal.hidden=true;status.hidden=false;status.textContent=exc.message;status.classList.add('error');input.value=''}
    finally{noteConfirm.disabled=false;noteConfirm.textContent='Importar e recalcular'}
  });
});
