(() => {
  const $ = id => document.getElementById(id);
  const money = value => Number(value || 0).toLocaleString('pt-BR', {style:'currency', currency:'BRL'});
  const number = value => {
    const text = String(value ?? '').trim().replace(/\s/g, '');
    const normalized = text.includes(',') ? text.replace(/\./g, '').replace(',', '.') : text;
    return Number(normalized) || 0;
  };
  const params = new URLSearchParams(location.search);
  const assetInput = $('payoffAsset'), spotInput = $('payoffSpot'), legsNode = $('payoffLegs');
  const defaultExpiry = new Date(Date.now()+30*86400000);
  const defaultMonthCode = kind => (kind === 'put' ? 'MNOPQRSTUVWX' : 'ABCDEFGHIJKL')[defaultExpiry.getMonth()];
  let chart;
  const defaultZoomLevel = 2.25;
  let zoomLevel = defaultZoomLevel;
  let currentMarkers = {jade:null, put:null, spot:null, tolerance:0};
  let legs = [
    {side:'short', kind:'put', code:`PETR${defaultMonthCode('put')}3200`, strike:32, premium:1.10, quantity:10},
    {side:'short', kind:'call', code:`PETR${defaultMonthCode('call')}3800`, strike:38, premium:1.20, quantity:10},
    {side:'long', kind:'call', code:`PETR${defaultMonthCode('call')}4400`, strike:44, premium:.60, quantity:10},
  ];

  function hydrateFromRadar() {
    if (!params.get('asset')) return;
    assetInput.value = params.get('asset').toUpperCase();
    spotInput.value = String(params.get('spot') || '').replace('.', ',');
    legs = [
      {side:'short', kind:'put', code:params.get('put') || '', strike:number(params.get('put_strike')), premium:number(params.get('put_premium')), quantity:1, delta:number(params.get('put_delta'))},
      {side:'short', kind:'call', code:params.get('short_call') || '', strike:number(params.get('short_call_strike')), premium:number(params.get('short_call_premium')), quantity:1},
      {side:'long', kind:'call', code:params.get('long_call') || '', strike:number(params.get('long_call_strike')), premium:number(params.get('long_call_premium')), quantity:1},
    ];
  }

  function legLabel(leg) { return `${leg.side === 'short' ? 'Venda' : 'Compra'} ${leg.kind.toUpperCase()}`; }
  function renderLegs() {
    legsNode.innerHTML = legs.map((leg, index) => `<article class="payoff-leg ${leg.side}" data-index="${index}"><div class="payoff-leg-row">
      <label><span class="leg-field-label">Operação</span><select data-field="side"><option value="short" ${leg.side==='short'?'selected':''}>Vender</option><option value="long" ${leg.side==='long'?'selected':''}>Comprar</option></select></label>
      <label><span class="leg-field-label">Tipo</span><select data-field="kind"><option value="put" ${leg.kind==='put'?'selected':''}>Put</option><option value="call" ${leg.kind==='call'?'selected':''}>Call</option></select></label>
      <label><span class="leg-field-label">Quantidade</span><input data-field="quantity" type="number" min="1" step="1" value="${leg.quantity}"></label>
      <span class="leg-expiry" data-leg-expiry>—</span>
      <label><span class="leg-field-label">Strike</span><input data-field="strike" type="number" min="0" step="0.01" value="${leg.strike}"></label>
      <label><span class="leg-field-label">Ticker</span><input data-field="code" value="${leg.code}" maxlength="14" placeholder="Ex.: PETRA320"></label>
      <span class="leg-delta">${leg.delta ? leg.delta.toFixed(2).replace('.',',') : '—'}</span>
      <span class="leg-distance" data-leg-distance>—</span>
      <label><span class="leg-field-label">Preço</span><input data-field="premium" type="number" min="0" step="0.01" value="${leg.premium}"></label>
      <strong class="leg-total" data-leg-total>—</strong>
      <strong class="leg-roi" data-leg-roi>—</strong>
      <button class="payoff-leg-remove" data-remove="${index}" type="button" aria-label="Remover ${legLabel(leg)}">×</button>
    </div></article>`).join('');
    $('legsCount').textContent = `${legs.length} perna${legs.length === 1 ? '' : 's'}`;
  }

  function inferKind(code, fallback) {
    const letter = String(code).toUpperCase().replace(/[^A-Z]/g, '').slice(-1);
    if ('ABCDEFGHIJKL'.includes(letter)) return 'call';
    if ('MNOPQRSTUVWX'.includes(letter)) return 'put';
    return fallback;
  }

  function syncLegs() {
    legsNode.querySelectorAll('.payoff-leg').forEach(card => {
      const leg = legs[Number(card.dataset.index)];
      card.querySelectorAll('[data-field]').forEach(input => {
        const field = input.dataset.field;
        leg[field] = ['strike','premium','quantity'].includes(field) ? number(input.value) : (field === 'code' ? input.value.toUpperCase() : input.value);
      });
      leg.kind = inferKind(leg.code, leg.kind);
    });
  }

  function refreshLegRows(spot) {
    const expiry = $('payoffExpiry').value;
    const expiryLabel = expiry ? new Date(`${expiry}T12:00:00`).toLocaleDateString('pt-BR') : '—';
    legsNode.querySelectorAll('.payoff-leg').forEach(card => {
      const leg = legs[Number(card.dataset.index)];
      const distance = spot ? (leg.strike / spot - 1) * 100 : 0;
      const signedTotal = (leg.side === 'short' ? 1 : -1) * leg.premium * leg.quantity * 100;
      card.querySelector('[data-leg-expiry]').textContent = expiryLabel;
      card.querySelector('[data-leg-distance]').textContent = `${distance >= 0 ? '+' : ''}${distance.toFixed(2).replace('.', ',')}%`;
      const total = card.querySelector('[data-leg-total]');
      total.textContent = money(signedTotal);
      total.classList.toggle('negative', signedTotal < 0);
      const roi = leg.strike ? (leg.side === 'short' ? 1 : -1) * leg.premium / leg.strike * 100 : 0;
      const roiNode = card.querySelector('[data-leg-roi]');
      roiNode.textContent = `${roi >= 0 ? '+' : ''}${roi.toFixed(2).replace('.', ',')}%`;
      roiNode.classList.toggle('negative', roi < 0);
    });
  }

  function legPayoff(leg, price) {
    const intrinsic = leg.kind === 'call' ? Math.max(price-leg.strike, 0) : Math.max(leg.strike-price, 0);
    const perShare = leg.side === 'long' ? intrinsic-leg.premium : leg.premium-intrinsic;
    return perShare * leg.quantity * 100;
  }

  function validate() {
    const root = assetInput.value.trim().toUpperCase().replace(/\d+$/, '');
    const invalid = legs.filter(leg => leg.code && !leg.code.toUpperCase().startsWith(root));
    const node = $('payoffValidation');
    node.classList.toggle('error', Boolean(invalid.length));
    node.textContent = invalid.length ? `Atenção: ${invalid.map(leg=>leg.code).join(', ')} não pertence ao ativo ${assetInput.value.toUpperCase()}.` : 'Todos os códigos pertencem ao mesmo ativo-base. O gráfico é atualizado automaticamente.';
    return !invalid.length;
  }

  function identify() {
    const types = legs.map(leg => `${leg.side}-${leg.kind}`).sort().join('|');
    if (types === 'long-call|short-call|short-put') return 'JADE LIZARD';
    if (types === 'long-call|short-call') return 'TRAVA DE ALTA/BAIXA';
    if (types === 'long-put|short-put') return 'TRAVA COM PUT';
    if (legs.length === 1 && legs[0].side === 'short' && legs[0].kind === 'put') return 'VENDA DE PUT';
    return 'ESTRUTURA PERSONALIZADA';
  }

  function breakEvens(points, values) {
    const result=[];
    for(let i=1;i<values.length;i++) if(values[i]===0 || values[i-1]*values[i]<0) {
      const x=points[i-1]+(0-values[i-1])*(points[i]-points[i-1])/(values[i]-values[i-1]);
      if(!result.some(item=>Math.abs(item-x)<.1)) result.push(x);
    }
    return result;
  }

  const hoverLine = {id:'payoffHoverLine', afterDraw(chart) {
    if (!chart.tooltip?._active?.length) return;
    const x=chart.tooltip._active[0].element.x, area=chart.chartArea, ctx=chart.ctx;
    ctx.save();ctx.setLineDash([5,5]);ctx.strokeStyle='#64748b';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(x,area.top);ctx.lineTo(x,area.bottom);ctx.stroke();ctx.restore();
  }};

  const breakEvenMarkerLines = {id:'breakEvenMarkerLines', afterDatasetsDraw(chart) {
    const area=chart.chartArea, scale=chart.scales.x, labels=chart.data.labels || [], ctx=chart.ctx;
    [{value:currentMarkers.jade,color:'#f59e0b'},{value:currentMarkers.put,color:'#8254d6'},{value:currentMarkers.spot,color:'#111827'}].forEach(marker => {
      if (!Number.isFinite(marker.value) || !labels.length) return;
      const min=Number(labels[0]), max=Number(labels[labels.length-1]);
      const firstX=scale.getPixelForValue(0), lastX=scale.getPixelForValue(labels.length-1);
      const x=firstX+(marker.value-min)/(max-min)*(lastX-firstX);
      ctx.save();ctx.setLineDash([7,6]);ctx.strokeStyle=marker.color;ctx.lineWidth=2.5;ctx.beginPath();ctx.moveTo(x,area.top);ctx.lineTo(x,area.bottom);ctx.stroke();ctx.restore();
    });
  }};

  function dockedTooltip(context) {
    const node = $('payoffTooltip'), floating = $('payoffFloatingTooltip'), tooltip = context.tooltip;
    if (!tooltip || tooltip.opacity === 0 || !tooltip.dataPoints?.length) {
      node.innerHTML = '<span>Passe o mouse pelo gráfico</span><strong>Os detalhes da estrutura e da PUT isolada aparecerão aqui, sem cobrir as curvas.</strong>';
      floating.hidden = true;
      return;
    }
    const price = Number(tooltip.dataPoints[0].label);
    const structure = tooltip.dataPoints.find(point => point.datasetIndex === 0)?.raw || 0;
    const put = tooltip.dataPoints.find(point => point.datasetIndex === 1)?.raw || 0;
    const spot = number(spotInput.value);
    const variation = `${spot ? ((price / spot - 1) * 100).toFixed(2).replace('.', ',') : '0,00'}%`;
    const jadeHint = Number.isFinite(currentMarkers.jade) && Math.abs(price-currentMarkers.jade)<=currentMarkers.tolerance ? `<em class="marker-hint jade-hint">Linha laranja: break-even da Jade (${money(currentMarkers.jade)}). Neste preço, o resultado da estrutura é zero.</em>` : '';
    const putHint = Number.isFinite(currentMarkers.put) && Math.abs(price-currentMarkers.put)<=currentMarkers.tolerance ? `<em class="marker-hint put-hint">Linha roxa: break-even da PUT isolada (${money(currentMarkers.put)}). Abaixo deste preço, a PUT entra em prejuízo.</em>` : '';
    const spotHint = Number.isFinite(currentMarkers.spot) && Math.abs(price-currentMarkers.spot)<=currentMarkers.tolerance ? `<em class="marker-hint spot-hint">Linha preta: preço atual da ação (${money(currentMarkers.spot)}). Ela mostra onde o ativo está hoje em relação aos break-evens.</em>` : '';
    node.innerHTML = `<span>Ativo em <b>${money(price)}</b></span><strong>Estrutura: ${money(structure)}</strong><strong class="put-detail">PUT isolada: ${money(put)}</strong><small>Variação sobre o preço atual: ${variation}</small>${jadeHint}${putHint}${spotHint}`;
    floating.innerHTML = `<span>Ativo em ${money(price)}</span><strong>Estrutura: ${money(structure)}</strong><b>PUT isolada: ${money(put)}</b><small>Variação: ${variation}</small>${jadeHint}${putHint}${spotHint}`;
    floating.hidden = false;
    const placeLeft = tooltip.caretX > context.chart.width * .65;
    floating.style.left = `${placeLeft ? Math.max(10, tooltip.caretX - 300) : tooltip.caretX + 90}px`;
    floating.style.top = 'auto';
    floating.style.bottom = '58px';
  }

  function update() {
    syncLegs(); validate();
    const spot = number(spotInput.value), strikes = legs.map(leg=>leg.strike).filter(Boolean);
    refreshLegRows(spot);
    const fullLow=Math.max(.01, Math.min(spot || 1, ...strikes)*.55), fullHigh=Math.max(spot || 1, ...strikes)*1.45;
    const center=spot || (fullLow+fullHigh)/2, half=(fullHigh-fullLow)/(2*zoomLevel);
    const low=Math.max(.01,center-half), high=center+half;
    const points=Array.from({length:121},(_,i)=>low+(high-low)*i/120);
    const structure=points.map(price=>legs.reduce((sum,leg)=>sum+legPayoff(leg,price),0));
    const shortPut=legs.find(leg=>leg.side==='short'&&leg.kind==='put');
    const putOnly=points.map(price=>shortPut?legPayoff(shortPut,price):0);
    const credit=legs.reduce((sum,leg)=>sum+(leg.side==='short'?1:-1)*leg.premium*leg.quantity*100,0);
    const maxProfit=Math.max(...structure), minProfit=Math.min(...structure);
    const putProfit=shortPut ? shortPut.premium*shortPut.quantity*100 : 0;
    const difference=putProfit ? (maxProfit-putProfit)/putProfit*100 : 0;
    const structureBreakEvens=breakEvens(points,structure);
    currentMarkers={jade:identify()==='JADE LIZARD' ? (structureBreakEvens[0] ?? null) : null,put:shortPut ? shortPut.strike-shortPut.premium : null,spot:spot || null,tolerance:(high-low)/120*1.25};
    $('netCredit').textContent=money(credit);$('maxProfit').textContent=money(maxProfit);$('maxLoss').textContent=money(Math.abs(Math.min(0,minProfit)));
    $('putOnlyProfit').textContent=money(putProfit);$('gainDifference').textContent=`${difference>=0?'+':''}${difference.toFixed(2).replace('.',',')}%`;
    $('breakEvens').textContent=structureBreakEvens.map(value=>money(value)).join(' · ')||'—';$('strategyName').textContent=identify();
    const data={labels:points.map(value=>value.toFixed(2)),datasets:[
      {label:'Estrutura completa',data:structure,borderColor:'#0b8f62',backgroundColor:'rgba(11,143,98,.12)',fill:'origin',borderWidth:3,pointRadius:0,tension:.08,segment:{borderColor:ctx=>ctx.p1.parsed.y<0?'#e54b59':'#0b8f62'}},
      {label:'Somente venda da PUT',data:putOnly,borderColor:'#8254d6',borderDash:[8,6],borderWidth:2.5,pointRadius:0,tension:.05,fill:false}
    ]};
    if(chart){chart.data=data;chart.update();return;}
    chart=new Chart($('payoffChart'),{type:'line',data,plugins:[breakEvenMarkerLines,hoverLine],options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},plugins:{legend:{display:false},tooltip:{enabled:false,external:dockedTooltip}},scales:{x:{grid:{display:false},title:{display:true,text:'Preço do ativo no vencimento'},ticks:{maxTicksLimit:12,callback:(_v,i)=>money(points[i])}},y:{grid:{color:ctx=>ctx.tick.value===0?'#25352e':'rgba(100,120,110,.12)',lineWidth:ctx=>ctx.tick.value===0?2:1},title:{display:true,text:'Lucro / Prejuízo'},ticks:{callback:value=>money(value)}}}}});
  }

  hydrateFromRadar();
  $('payoffExpiry').value=defaultExpiry.toISOString().slice(0,10);
  renderLegs(); update();
  document.addEventListener('input', event=>{if(event.target.closest('.payoff-page')) update()});
  assetInput.addEventListener('input',()=>{renderLegs();update()});
  legsNode.addEventListener('change',()=>{update();renderLegs()});
  document.addEventListener('click',event=>{const remove=event.target.closest('[data-remove]');if(remove){syncLegs();legs.splice(Number(remove.dataset.remove),1);renderLegs();update();}});
  $('addPayoffLeg').addEventListener('click',()=>{syncLegs();legs.push({side:'long',kind:'call',code:'',strike:number(spotInput.value),premium:0,quantity:1});renderLegs();update();});
  $('payoffClear').addEventListener('click',()=>{legs=[];renderLegs();update()});
  $('payoffZoomIn').addEventListener('click',()=>{zoomLevel=Math.min(zoomLevel*1.5,5);update()});
  $('payoffZoomOut').addEventListener('click',()=>{zoomLevel=Math.max(zoomLevel/1.5,1);update()});
  $('payoffZoomReset').addEventListener('click',()=>{zoomLevel=defaultZoomLevel;update()});
  $('payoffSave').addEventListener('click',event=>{syncLegs();localStorage.setItem('faculdademaria.payoff',JSON.stringify({asset:assetInput.value,spot:spotInput.value,expiry:$('payoffExpiry').value,legs}));event.currentTarget.textContent='✓ Simulação salva';setTimeout(()=>event.currentTarget.textContent='Salvar Simulação',1600)});
})();
