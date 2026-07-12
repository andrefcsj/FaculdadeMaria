document.addEventListener('DOMContentLoaded',()=>{
  const input=document.getElementById('newBrokerageNote');
  const result=document.getElementById('brokerageImportResult');
  const footer=document.getElementById('newOperationFooterHint');
  if(!input||!result)return;
  let note=null;
  let selectedTrade=null;
  const q=id=>document.getElementById(id);
  const brl=value=>new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(Number(value)||0);
  function applyTrade(index){
    selectedTrade=note.trades[Number(index)];
    if(!selectedTrade)return;
    q('newOptionCode').value=selectedTrade.option_code;
    q('newContracts').value=selectedTrade.contracts;
    q('newPremium').value=brl(selectedTrade.unit_price);
    q('newCosts').value=brl(selectedTrade.allocated_costs);
    q('newIrrf').value=brl(selectedTrade.allocated_irrf);
    const strategy=document.querySelector(`input[name="Estrategia"][value="${selectedTrade.side}"]`);
    if(strategy)strategy.checked=true;
    const typeValue=selectedTrade.market.toLowerCase().includes('venda')?'PUT':'CALL';
    const type=document.querySelector(`input[name="Tipo"][value="${typeValue}"]`);
    if(type)type.checked=true;
    q('newOptionCode').dispatchEvent(new Event('input',{bubbles:true}));
    q('newPremium').dispatchEvent(new Event('change',{bubbles:true}));
    footer.textContent=`Nota ${note.note_number} de ${new Date(note.trade_date+'T12:00:00').toLocaleDateString('pt-BR')} será vinculada à operação. Confira strike e vencimento antes de salvar.`;
  }
  input.addEventListener('change',async()=>{
    const file=input.files?.[0];if(!file)return;
    result.hidden=false;result.innerHTML='<strong>Lendo nota BTG/Necton...</strong>';
    const body=new FormData();body.append('brokerage_note',file);
    try{
      const response=await fetch('/api/notas-corretagem/analisar',{method:'POST',body});
      const data=await response.json();
      if(!response.ok||!data.ok)throw new Error(data.error||'Não foi possível ler a nota.');
      note=data.note;
      const options=note.trades.map((trade,index)=>`<option value="${index}">${trade.option_code} • ${trade.side} • ${trade.quantity} opções • ${brl(trade.gross_value)}</option>`).join('');
      result.innerHTML=`<strong>Nota ${note.note_number} reconhecida</strong><br>Crédito/débito líquido: ${brl(note.net_cash)} • Custos efetivos: ${brl(note.operational_costs)}<select id="brokerageTradeSelect" aria-label="Selecione a operação da nota">${options}</select><small>O PDF não será armazenado. Confira os campos antes de cadastrar.</small>`;
      document.getElementById('brokerageTradeSelect').addEventListener('change',event=>applyTrade(event.target.value));
      applyTrade(0);
    }catch(error){note=null;selectedTrade=null;result.innerHTML=`<strong>Não foi possível importar:</strong> ${error.message}`;}
  });
  const originalFetch=window.fetch.bind(window);
  window.fetch=async(resource,options={})=>{
    const url=typeof resource==='string'?resource:resource?.url;
    if(url==='/api/operacoes'&&note&&selectedTrade&&options.body&&String(options.headers?.['Content-Type']||'').includes('application/json')){
      try{
        const payload=JSON.parse(options.body);
        payload.Data_abertura=note.trade_date;
        payload.Nota_corretagem={...note,trade:selectedTrade};
        options={...options,body:JSON.stringify(payload)};
      }catch(_error){}
    }
    return originalFetch(resource,options);
  };
});
