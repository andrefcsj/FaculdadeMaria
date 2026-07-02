
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

  money(document.getElementById('premio'));
  money(document.getElementById('custos'));
  money(document.getElementById('irrf'));

});
