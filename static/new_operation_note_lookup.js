document.addEventListener('brokerage-trade-applied',async event=>{
  const code=String(event.detail?.optionCode||'').trim().toUpperCase();
  if(!code)return;
  const q=id=>document.getElementById(id),hint=q('newOptionHint'),strike=q('newStrike'),expiry=q('newExpiry'),spot=q('newSpot'),under=q('newUnderlying');
  const brl=value=>new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(Number(value)||0);
  if(hint)hint.textContent='Buscando strike e vencimento da opção importada...';
  try{
    const response=await fetch(`/api/opcoes/${encodeURIComponent(code)}`),data=await response.json();
    if(!response.ok||!data.ok)throw new Error(data.error||'Consulta indisponível');
    if(data.asset&&under)under.value=data.asset;
    if(data.strike&&strike)strike.value=brl(data.strike);
    if(data.expiry&&expiry)expiry.value=data.expiry;
    if(data.spot_price&&spot)spot.value=brl(data.spot_price);
    if(hint)hint.textContent=data.strike?`Strike e vencimento preenchidos via ${data.source}.`:'Código reconhecido, mas o strike não consta no mercado carregado.';
    strike?.dispatchEvent(new Event('change',{bubbles:true}));
  }catch(_error){if(hint)hint.textContent='Não foi possível localizar o strike. Atualize a B3/CSV ou confira manualmente.'}
});
