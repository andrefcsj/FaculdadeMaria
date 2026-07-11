
document.addEventListener("DOMContentLoaded", () => {

  if (typeof Chart === "undefined") return;

  const lucro = document.getElementById("lucroChart");
  if (lucro) {
    new Chart(lucro, {
      type: "line",
      data: {
        labels: ["Jan","Fev","Mar","Abr","Mai","Jun"],
        datasets: [{
          label: "Lucro",
          data: [0,0,0,0,0,0],
          borderColor: "#4d8cff",
          borderWidth:3,
          fill:true,
          backgroundColor:"rgba(77,140,255,.12)",
          tension: 0.3
        }]
      },
      options: {responsive:true, plugins:{legend:{display:false}}}
    });
  }

  const premios = document.getElementById("premiosChart");
  if (premios) {
    new Chart(premios, {
      type: "bar",
      data: {
        labels: ["Jan","Fev","Mar","Abr","Mai","Jun"],
        datasets: [{
          data: [0,0,0,0,0,0],
          backgroundColor: "rgba(70,232,91,.8)",
          borderRadius:8
        }]
      },
      options: {responsive:true, plugins:{legend:{display:false}}}
    });
  }

  const pizza = document.getElementById("pizzaChart");
  if (pizza) {
    new Chart(pizza, {
      type: "doughnut",
      data: {
        labels: ["Sem dados"],
        datasets: [{
          data: [100]
        }]
      },
      options: {responsive:true}
    });
  }


  const patrimonio = document.getElementById("patrimonioChart");
  if (patrimonio) {
    new Chart(patrimonio, {
      type: "line",
      data: {
        labels: ["Jan","Fev","Mar","Abr","Mai","Jun"],
        datasets: [{
          data: [5392,5392,5392,5392,5392,5392],
          borderColor: "#b06cff",
          tension: 0.3
        }]
      },
      options: {responsive:true, plugins:{legend:{display:false}}}
    });
  }


  window.cortexIndicators = {
    roiAbertas: 2.93,
    roiFechadas: 1.75,
    patrimonio: 5392
  };

});


document.addEventListener('DOMContentLoaded',()=>{
 const codigo=document.getElementById('codigo_opcao');
 if(codigo){
   codigo.addEventListener('input',()=>codigo.value=codigo.value.toUpperCase());
 }
 const contratos=document.querySelector('[name="contratos"]');
 if(contratos){
   contratos.addEventListener('change',()=>{
      let v=parseInt(contratos.value||0);
      contratos.value = Math.round(v/100)*100;
   });
 }
});


document.addEventListener('DOMContentLoaded',()=>{

  const codigo=document.getElementById('codigo_opcao');
  if(codigo){
    codigo.addEventListener('input',()=>{
      codigo.value = codigo.value.toUpperCase();
    });
  }

  const contratos=document.getElementById('contratos');
  const info=document.getElementById('acoesInfo');

  if(contratos && info){
    contratos.addEventListener('input',()=>{
      const v = parseInt(contratos.value || 0);
      info.innerHTML = (v*100).toLocaleString('pt-BR') + ' ações';
    });
  }

  function money(el){
    if(!el) return;
    el.addEventListener('input',()=>{
      let v = el.value.replace(/\D/g,'');
      v = (Number(v)/100).toLocaleString('pt-BR',{
        style:'currency',
        currency:'BRL'
      });
      el.value = v;
    });
  }

  
  money(document.getElementById('strike'));

  money(document.getElementById('premio'));
  money(document.getElementById('custos'));
  money(document.getElementById('irrf'));

});


document.addEventListener('DOMContentLoaded',()=>{

 const form=document.querySelector('.op-form');
 const strike=document.getElementById('strike');
 const contratos=document.getElementById('contratos');
 const premio=document.getElementById('premio');

 function parseBRL(v){
   if(!v) return 0;
   return Number(String(v).replace(/[^0-9,]/g,'').replace(',','.')) || 0;
 }

 function moeda(v){
   return v.toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
 }

 function atualizarResumo(){
    const s = parseFloat(strike?.value || 0);
    const c = parseInt(contratos?.value || 0);
    const p = parseBRL(premio?.value);

    const capital = s * c * 100;
    const premioBruto = p * c * 100;
    const custos = parseBRL(document.getElementById('custos')?.value);
    const irrf = parseBRL(document.getElementById('irrf')?.value);
    const premioLiquido = premioBruto - custos - irrf;
    const roi = capital > 0 ? (premioLiquido / capital) * 100 : 0;

    const a=document.getElementById('capitalCalc');
    const b=document.getElementById('premioCalc');
    const r=document.getElementById('roiCalc');

    if(a) a.innerHTML = moeda(capital);
    if(b) b.innerHTML = moeda(premioLiquido);
    if(r) r.innerHTML = roi.toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2}) + '%';
 }

 [strike, contratos, premio, document.getElementById('custos'), document.getElementById('irrf')].forEach(el=>{
   if(el) el.addEventListener('input', atualizarResumo);
 });

 if(form){
   form.addEventListener('submit',(e)=>{
      const codigo=document.getElementById('codigo_opcao')?.value.trim();
      const venc=form.querySelector('[name="Vencimento"]')?.value;

      if(!codigo || !strike.value || !contratos.value || !premio.value || !venc){
         e.preventDefault();
         alert('Preencha todos os campos obrigatórios.');
         return;
      }

      sessionStorage.setItem('cortexToast','1');

      const status=form.querySelector('[name="Status"]').value;
      if(status==='Encerrada'){
         setTimeout(()=>window.location='/op-fechadas',500);
      }
   });
 }

 if(sessionStorage.getItem('cortexToast')){
    sessionStorage.removeItem('cortexToast');
    const toast=document.createElement('div');
    toast.innerHTML='✅ Operação salva com sucesso!';
    toast.style.cssText='position:fixed;top:20px;right:20px;background:#18a957;color:#fff;padding:14px 20px;border-radius:14px;z-index:9999;font-weight:700';
    document.body.appendChild(toast);
    setTimeout(()=>toast.remove(),3000);
 }

 atualizarResumo();
});


function parseNumeroBR(v){
  if(!v) return 0;
  return Number(
    String(v)
      .replace(/[^0-9,]/g,'')
      .replace('.','')
      .replace(',','.')
  ) || 0;
}

document.addEventListener('DOMContentLoaded',()=>{

  const strike=document.getElementById('strike');
  const contratos=document.getElementById('contratos');
  const premio=document.getElementById('premio');
  const vencimento=document.querySelector('[name="Vencimento"]');

  document.querySelectorAll('.toggle-op:not(.toggle-buy) button').forEach(btn=>{
    btn.addEventListener('click',()=>{
      document.querySelectorAll('.toggle-op:not(.toggle-buy) button').forEach(b=>b.classList.remove('active'));
      btn.classList.add('active');
    });
  });

  document.querySelectorAll('.toggle-buy button').forEach(btn=>{
    btn.addEventListener('click',()=>{
      document.querySelectorAll('.toggle-buy button').forEach(b=>b.classList.remove('active'));
      btn.classList.add('active');
    });
  });

  if(vencimento){
    vencimento.addEventListener('change',()=>vencimento.blur());
  }

  function atualizarResumo2(){
    const s=parseNumeroBR(strike?.value);
    const c=parseInt(contratos?.value||0);
    const p=parseNumeroBR((premio?.value||'').replace(/[R$\s]/g,''));

    const capital=s*c*100;
    const premioBruto=p*c*100;
    const custos=parseNumeroBR((document.getElementById('custos')?.value||'').replace(/[R$\s]/g,''));
    const irrf=parseNumeroBR((document.getElementById('irrf')?.value||'').replace(/[R$\s]/g,''));
    const premioLiquido=premioBruto-custos-irrf;
    const roi=capital>0?(premioLiquido/capital)*100:0;

    const moeda=v=>v.toLocaleString('pt-BR',{style:'currency',currency:'BRL'});

    const a=document.getElementById('capitalCalc');
    const b=document.getElementById('premioCalc');
    const r=document.getElementById('roiCalc');

    if(a) a.innerHTML=moeda(capital);
    if(b) b.innerHTML=moeda(premioLiquido);
    if(r) r.innerHTML=roi.toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2})+'%';
  }

  [strike,contratos,premio,document.getElementById('custos'),document.getElementById('irrf')].forEach(el=>{
    if(el) el.addEventListener('input', atualizarResumo2);
  });

  const oldRemove=setTimeout;
  if(sessionStorage.getItem('cortexToast')){
    sessionStorage.removeItem('cortexToast');
    const toast=document.createElement('div');
    toast.innerHTML='✅ Operação salva com sucesso!';
    toast.style.cssText='position:fixed;top:20px;right:20px;background:linear-gradient(90deg,#16a34a,#22c55e);color:#fff;padding:16px 22px;border-radius:16px;z-index:9999;font-weight:700;box-shadow:0 15px 40px rgba(34,197,94,.35)';
    document.body.appendChild(toast);
    oldRemove(()=>toast.remove(),6000);
  }
});

document.addEventListener('DOMContentLoaded',()=>{
 document.querySelectorAll('.toggle-buy button').forEach(btn=>{
   btn.addEventListener('click',()=>{
      document.querySelectorAll('.toggle-buy button').forEach(b=>b.classList.remove('active'));
      btn.classList.add('active');
   });
 });
});

document.addEventListener('DOMContentLoaded',()=>{
  const dataNode=document.getElementById('executiveDashboardData');
  const canvas=document.getElementById('executivePremiumChart');
  if(dataNode && canvas && typeof Chart !== 'undefined'){
    const data=JSON.parse(dataNode.textContent || '{}');
    new Chart(canvas,{
      type:'line',
      data:{
        labels:data.labels || [],
        datasets:[{
          label:'Prêmios',
          data:data.premiums || [],
          borderColor:'#0b2b59',
          backgroundColor:'rgba(197,139,24,.12)',
          pointBackgroundColor:'#c58b18',
          pointBorderColor:'#fff',
          pointBorderWidth:2,
          pointRadius:4,
          borderWidth:2.5,
          fill:true,
          tension:.34
        }]
      },
      options:{
        responsive:true,
        maintainAspectRatio:false,
        plugins:{legend:{display:false},tooltip:{callbacks:{label:(ctx)=>Number(ctx.raw||0).toLocaleString('pt-BR',{style:'currency',currency:'BRL'})}}},
        scales:{
          x:{grid:{display:false},ticks:{color:'#718096',font:{size:10}}},
          y:{grid:{color:'rgba(16,33,60,.07)'},ticks:{color:'#718096',font:{size:10},callback:(value)=>Number(value).toLocaleString('pt-BR',{style:'currency',currency:'BRL',maximumFractionDigits:0})}}
        }
      }
    });
  }

  const updated=document.getElementById('lastUpdated');
  if(updated){
    updated.textContent=new Date().toLocaleString('pt-BR',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});
  }
  const headerUpdated=document.getElementById('headerUpdated');
  if(headerUpdated){
    headerUpdated.textContent=new Date().toLocaleString('pt-BR',{day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'});
  }

  const themeButton=document.getElementById('themeButton');
  if(themeButton){
    themeButton.addEventListener('click',()=>{
      const checkbox=document.getElementById('themeToggle');
      if(checkbox){ checkbox.click(); return; }
      document.body.classList.toggle('light');
      localStorage.setItem('theme',document.body.classList.contains('light')?'light':'dark');
    });
  }
});
