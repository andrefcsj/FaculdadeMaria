(() => {
  const $ = id => document.getElementById(id);
  const money = value => Number(value || 0).toLocaleString('pt-BR', {style:'currency', currency:'BRL'});
  const number = value => Number(String(value ?? '').replace(/\./g, '').replace(',', '.')) || 0;
  const params = new URLSearchParams(location.search);
  const assetInput = $('payoffAsset'), spotInput = $('payoffSpot'), legsNode = $('payoffLegs');
  let chart;
  let legs = [
    {side:'short', kind:'put', code:'PETRP3200', strike:32, premium:1.10, quantity:10},
    {side:'short', kind:'call', code:'PETRC3800', strike:38, premium:1.20, quantity:10},
    {side:'long', kind:'call', code:'PETRC4400', strike:44, premium:.60, quantity:10},
  ];

  function hydrateFromRadar() {
    if (!params.get('asset')) return;
    assetInput.value = params.get('asset').toUpperCase();
    spotInput.value = String(params.get('spot') || '').replace('.', ',');
    legs = [
      {side:'short', kind:'put', code:params.get('put') || '', strike:number(params.get('put_strike')), premium:number(params.get('put_premium')), quantity:1},
      {side:'short', kind:'call', code:params.get('short_call') || '', strike:number(params.get('short_call_strike')), premium:number(params.get('short_call_premium')), quantity:1},
      {side:'long', kind:'call', code:params.get('long_call') || '', strike:number(params.get('long_call_strike')), premium:number(params.get('long_call_premium')), quantity:1},
    ];
  }

  function legLabel(leg) { return `${leg.side === 'short' ? 'Venda' : 'Compra'} ${leg.kind.toUpperCase()}`; }
  function renderLegs() {
    legsNode.innerHTML = legs.map((leg, index) => `<article class="payoff-leg ${leg.side}" data-index="${index}"><div class="payoff-leg-row">
      <label>Operação<select data-field="side"><option value="short" ${leg.side==='short'?'selected':''}>Venda</option><option value="long" ${leg.side==='long'?'selected':''}>Compra</option></select></label>
      <label>Código da opção<input data-field="code" value="${leg.code}" maxlength="14" placeholder="Ex.: PETRA320"></label>
      <label>Strike<input data-field="strike" inputmode="decimal" value="${String(leg.strike).replace('.',',')}"></label>
      <label>Prêmio<input data-field="premium" inputmode="decimal" value="${String(leg.premium).replace('.',',')}"></label>
      <label>Qtd.<input data-field="quantity" type="number" min="1" value="${leg.quantity}"></label>
      <button class="payoff-leg-remove" data-remove="${index}" type="button" aria-label="Remover ${legLabel(leg)}">×</button>
    </div><small>${legLabel(leg)} · ativo-base <strong>${assetInput.value.toUpperCase()}</strong></small></article>`).join('');
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

  function update() {
    syncLegs(); validate();
    const spot = number(spotInput.value), strikes = legs.map(leg=>leg.strike).filter(Boolean);
    const low=Math.max(.01, Math.min(spot || 1, ...strikes)*.55), high=Math.max(spot || 1, ...strikes)*1.45;
    const points=Array.from({length:121},(_,i)=>low+(high-low)*i/120);
    const structure=points.map(price=>legs.reduce((sum,leg)=>sum+legPayoff(leg,price),0));
    const shortPut=legs.find(leg=>leg.side==='short'&&leg.kind==='put');
    const putOnly=points.map(price=>shortPut?legPayoff(shortPut,price):0);
    const credit=legs.reduce((sum,leg)=>sum+(leg.side==='short'?1:-1)*leg.premium*leg.quantity*100,0);
    const maxProfit=Math.max(...structure), minProfit=Math.min(...structure);
    const putProfit=shortPut ? shortPut.premium*shortPut.quantity*100 : 0;
    const difference=putProfit ? (maxProfit-putProfit)/putProfit*100 : 0;
    $('netCredit').textContent=money(credit);$('maxProfit').textContent=money(maxProfit);$('maxLoss').textContent=money(Math.abs(Math.min(0,minProfit)));
    $('putOnlyProfit').textContent=money(putProfit);$('gainDifference').textContent=`${difference>=0?'+':''}${difference.toFixed(2).replace('.',',')}%`;
    $('breakEvens').textContent=breakEvens(points,structure).map(value=>money(value)).join(' · ')||'—';$('strategyName').textContent=identify();
    const data={labels:points.map(value=>value.toFixed(2)),datasets:[
      {label:'Estrutura completa',data:structure,borderColor:'#0b8f62',backgroundColor:'rgba(11,143,98,.12)',fill:'origin',borderWidth:3,pointRadius:0,tension:.08,segment:{borderColor:ctx=>ctx.p1.parsed.y<0?'#e54b59':'#0b8f62'}},
      {label:'Somente venda da PUT',data:putOnly,borderColor:'#8254d6',borderDash:[8,6],borderWidth:2.5,pointRadius:0,tension:.05,fill:false}
    ]};
    if(chart){chart.data=data;chart.update();return;}
    chart=new Chart($('payoffChart'),{type:'line',data,plugins:[hoverLine],options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},plugins:{legend:{display:false},tooltip:{displayColors:true,callbacks:{title:items=>`Ativo em ${money(items[0].label)}`,label:ctx=>`${ctx.dataset.label}: ${money(ctx.raw)}`,afterBody:items=>{const price=Number(items[0].label);return [`Preço atual: ${money(spot)}`,`Variação até o ponto: ${spot?((price/spot-1)*100).toFixed(2).replace('.',','):'0,00'}%`]}}}},scales:{x:{grid:{display:false},title:{display:true,text:'Preço do ativo no vencimento'},ticks:{maxTicksLimit:12,callback:(_v,i)=>money(points[i])}},y:{grid:{color:ctx=>ctx.tick.value===0?'#25352e':'rgba(100,120,110,.12)',lineWidth:ctx=>ctx.tick.value===0?2:1},title:{display:true,text:'Lucro / Prejuízo'},ticks:{callback:value=>money(value)}}}}});
  }

  hydrateFromRadar();
  $('payoffExpiry').value=new Date(Date.now()+30*86400000).toISOString().slice(0,10);
  renderLegs(); update();
  document.addEventListener('input', event=>{if(event.target.closest('.payoff-page')) update()});
  assetInput.addEventListener('input',()=>{renderLegs();update()});
  legsNode.addEventListener('change',()=>{update();renderLegs()});
  document.addEventListener('click',event=>{const remove=event.target.closest('[data-remove]');if(remove){syncLegs();legs.splice(Number(remove.dataset.remove),1);renderLegs();update();}});
  $('addPayoffLeg').addEventListener('click',()=>{syncLegs();legs.push({side:'long',kind:'call',code:'',strike:number(spotInput.value),premium:0,quantity:1});renderLegs();update();});
  $('payoffClear').addEventListener('click',()=>{legs=[];renderLegs();update()});
  $('payoffSave').addEventListener('click',event=>{syncLegs();localStorage.setItem('faculdademaria.payoff',JSON.stringify({asset:assetInput.value,spot:spotInput.value,expiry:$('payoffExpiry').value,legs}));event.currentTarget.textContent='✓ Simulação salva';setTimeout(()=>event.currentTarget.textContent='Salvar Simulação',1600)});
})();
