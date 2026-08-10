(()=>{
  const modal=document.getElementById('calculationSimulator');
  if(!modal)return;
  const $=id=>document.getElementById(id);
  const fields=['calcQuantity','calcAveragePrice','calcSpotPrice','calcStrike','calcPremium','calcCosts','calcTaxRate','calcTargetRoi'];
  const number=value=>{const raw=String(value||'').replace(/R\$|%|\s/g,'');if(!raw)return 0;return Number(raw.includes(',')?raw.replace(/\./g,'').replace(',','.'):raw)||0};
  const money=value=>(Number.isFinite(value)?value:0).toLocaleString('pt-BR',{style:'currency',currency:'BRL',minimumFractionDigits:2});
  const percent=value=>`${(Number.isFinite(value)?value:0).toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2})}%`;
  const calculate=()=>{
    const quantity=Math.max(1,Math.trunc(number($('calcQuantity').value))||1),average=number($('calcAveragePrice').value),spot=number($('calcSpotPrice').value),strike=number($('calcStrike').value),premium=number($('calcPremium').value),costs=Math.max(0,number($('calcCosts').value)),rate=Math.max(0,number($('calcTaxRate').value))/100,target=Math.max(0,number($('calcTargetRoi').value));
    const capital=average*quantity,grossExercise=(strike+premium-average)*quantity-costs,taxExercise=Math.max(grossExercise,0)*rate,netExercise=grossExercise-taxExercise,roi=capital?netExercise/capital*100:0,effectiveExit=quantity?(strike*quantity+premium*quantity-costs-taxExercise)/quantity:0;
    const premiumGross=premium*quantity-costs,premiumTax=Math.max(premiumGross,0)*rate,netPremium=premiumGross-premiumTax,adjustedAverage=quantity?average-netPremium/quantity:0;
    const desiredNet=capital*target/100,requiredGross=rate<1?desiredNet/(1-rate):0,requiredPremium=Math.max(0,average+(requiredGross+costs)/quantity-strike),requiredCombination=average+(requiredGross+costs)/quantity;
    $('calcNetRoi').textContent=percent(roi);$('calcNetProfit').textContent=money(netExercise);$('calcTax').textContent=money(taxExercise);$('calcEffectiveExit').textContent=money(effectiveExit);$('calcNetPremium').textContent=money(netPremium);$('calcAdjustedAverage').textContent=money(adjustedAverage);$('calcRequiredPremium').textContent=`Prêmio mínimo: ${money(requiredPremium)} por ação`;$('calcRequiredCombination').textContent=`Strike + prêmio necessários: ${money(requiredCombination)}`;$('calcStrikeDistance').textContent=spot&&strike?percent((strike/spot-1)*100):'--';
    const hero=modal.querySelector('.calc-result--hero'),complete=average>0&&strike>0;hero.classList.toggle('goal-missed',complete&&roi<target);$('calcGoalStatus').textContent=!complete?'Preencha preço médio, strike e prêmio':roi>=target?`Meta de ${percent(target)} atingida`:`Faltam ${percent(target-roi)} para a meta`;
  };
  const open=event=>{event?.preventDefault();modal.hidden=false;modal.setAttribute('aria-hidden','false');document.body.classList.add('calc-simulator-open');setTimeout(()=>$('calcAsset').focus(),30);calculate()};
  const close=()=>{modal.hidden=true;modal.setAttribute('aria-hidden','true');document.body.classList.remove('calc-simulator-open')};
  document.querySelectorAll('[data-open-calculation-simulator]').forEach(button=>button.addEventListener('click',open));modal.querySelectorAll('[data-close-calculation-simulator]').forEach(button=>button.addEventListener('click',close));
  fields.forEach(id=>$(id).addEventListener('input',calculate));$('calcAsset').addEventListener('input',event=>event.target.value=event.target.value.toUpperCase());
  modal.querySelector('[data-reset-calculation-simulator]').addEventListener('click',()=>{$('calculationSimulatorForm').reset();$('calcAsset').value='';calculate();$('calcAsset').focus()});
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!modal.hidden)close()});calculate();
})();
