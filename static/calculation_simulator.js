(()=>{
  const modal=document.getElementById('calculationSimulator');
  if(!modal)return;
  const $=id=>document.getElementById(id);
  const callFields=['calcQuantity','calcAveragePrice','calcSpotPrice','calcStrike','calcPremium','calcCosts','calcTaxRate','calcTargetRoi'];
  const putFields=['putCalcCurrentQuantity','putCalcCurrentAverage','putCalcSpot','putCalcContracts','putCalcContractSize','putCalcStrike','putCalcPremium','putCalcCosts','putCalcTaxRate'];
  const number=value=>{const raw=String(value||'').replace(/R\$|%|\s/g,'');if(!raw)return 0;return Number(raw.includes(',')?raw.replace(/\./g,'').replace(',','.'):raw)||0};
  const money=value=>(Number.isFinite(value)?value:0).toLocaleString('pt-BR',{style:'currency',currency:'BRL',minimumFractionDigits:2});
  const percent=value=>`${(Number.isFinite(value)?value:0).toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2})}%`;
  const calculateCall=()=>{
    const quantity=Math.max(1,Math.trunc(number($('calcQuantity').value))||1),average=number($('calcAveragePrice').value),spot=number($('calcSpotPrice').value),strike=number($('calcStrike').value),premium=number($('calcPremium').value),costs=Math.max(0,number($('calcCosts').value)),rate=Math.max(0,number($('calcTaxRate').value))/100,target=Math.max(0,number($('calcTargetRoi').value));
    const capital=average*quantity,grossExercise=(strike+premium-average)*quantity-costs,taxExercise=Math.max(grossExercise,0)*rate,netExercise=grossExercise-taxExercise,roi=capital?netExercise/capital*100:0,effectiveExit=quantity?(strike*quantity+premium*quantity-costs-taxExercise)/quantity:0;
    const premiumGross=premium*quantity-costs,premiumTax=Math.max(premiumGross,0)*rate,netPremium=premiumGross-premiumTax,adjustedAverage=quantity?average-netPremium/quantity:0;
    $('calcNetRoi').textContent=percent(roi);$('calcNetProfit').textContent=money(netExercise);$('calcTax').textContent=money(taxExercise);$('calcEffectiveExit').textContent=money(effectiveExit);$('calcNetPremium').textContent=money(netPremium);$('calcAdjustedAverage').textContent=money(adjustedAverage);$('calcStrikeDistance').textContent=spot&&strike?percent((strike/spot-1)*100):'--';
    const hero=modal.querySelector('[data-calculation-panel="call"] .calc-result--hero'),complete=average>0&&strike>0;hero.classList.toggle('goal-missed',complete&&roi<target);$('calcGoalStatus').textContent=!complete?'Preencha preço médio, strike e prêmio':roi>=target?`Meta de ${percent(target)} atingida`:`Faltam ${percent(target-roi)} para a meta`;
  };
  const calculatePut=()=>{
    const currentQuantity=Math.max(0,Math.trunc(number($('putCalcCurrentQuantity').value))||0),currentAverage=Math.max(0,number($('putCalcCurrentAverage').value)),spot=Math.max(0,number($('putCalcSpot').value)),contracts=Math.max(1,Math.trunc(number($('putCalcContracts').value))||1),contractSize=Math.max(1,Math.trunc(number($('putCalcContractSize').value))||100),strike=Math.max(0,number($('putCalcStrike').value)),premium=Math.max(0,number($('putCalcPremium').value)),costs=Math.max(0,number($('putCalcCosts').value)),rate=Math.max(0,number($('putCalcTaxRate').value))/100;
    const assignedQuantity=contracts*contractSize,grossPremium=premium*assignedQuantity-costs,tax=Math.max(grossPremium,0)*rate,netPremium=grossPremium-tax,premiumPerAssignedShare=assignedQuantity?netPremium/assignedQuantity:0,requiredCapital=strike*assignedQuantity,newLotAverage=Math.max(strike-premiumPerAssignedShare,0),combinedQuantity=currentQuantity+assignedQuantity,consolidatedAverage=combinedQuantity?((currentAverage*currentQuantity)+requiredCapital-netPremium)/combinedQuantity:newLotAverage,expiredAverage=currentQuantity?Math.max(currentAverage-netPremium/currentQuantity,0):null;
    $('putCalcAssignedQuantity').textContent=assignedQuantity.toLocaleString('pt-BR');$('putCalcRequiredCapital').textContent=money(requiredCapital);$('putCalcNetPremium').textContent=money(netPremium);$('putCalcNewLotAverage').textContent=money(newLotAverage);$('putCalcPremiumDiscount').textContent=`${money(premiumPerAssignedShare)}/ação`;$('putCalcConsolidatedAverage').textContent=money(consolidatedAverage);$('putCalcAverageAfterAssignment').textContent=money(consolidatedAverage);$('putCalcAverageIfExpired').textContent=expiredAverage===null?'Não possui ações':money(expiredAverage);$('putCalcStrikeDistance').textContent=spot&&strike?percent((strike/spot-1)*100):'--';
    $('putCalcPositionStatus').textContent=!strike?'Informe strike e prêmio da PUT':currentQuantity&&currentAverage?`${currentQuantity.toLocaleString('pt-BR')} ações atuais + ${assignedQuantity.toLocaleString('pt-BR')} no exercício`:`PM líquido para as ${assignedQuantity.toLocaleString('pt-BR')} ações adquiridas`;
  };
  const switchTab=tab=>{
    modal.querySelectorAll('[data-calculation-tab]').forEach(button=>button.classList.toggle('active',button.dataset.calculationTab===tab));
    modal.querySelectorAll('[data-calculation-panel]').forEach(panel=>panel.hidden=panel.dataset.calculationPanel!==tab);
    $('calcSimulatorStrategy').textContent=tab==='put'?'PUT VENDIDA':'CALL COBERTA';
    (tab==='put'?$('putCalcAsset'):$('calcAsset')).focus();
  };
  const open=event=>{event?.preventDefault();modal.hidden=false;modal.setAttribute('aria-hidden','false');document.body.classList.add('calc-simulator-open');setTimeout(()=>modal.querySelector('[data-calculation-tab].active')?.click(),30);calculateCall();calculatePut()};
  const close=()=>{modal.hidden=true;modal.setAttribute('aria-hidden','true');document.body.classList.remove('calc-simulator-open')};
  document.querySelectorAll('[data-open-calculation-simulator]').forEach(button=>button.addEventListener('click',open));modal.querySelectorAll('[data-close-calculation-simulator]').forEach(button=>button.addEventListener('click',close));modal.querySelectorAll('[data-calculation-tab]').forEach(button=>button.addEventListener('click',()=>switchTab(button.dataset.calculationTab)));
  callFields.forEach(id=>$(id).addEventListener('input',calculateCall));putFields.forEach(id=>$(id).addEventListener('input',calculatePut));['calcAsset','putCalcAsset'].forEach(id=>$(id).addEventListener('input',event=>event.target.value=event.target.value.toUpperCase()));
  modal.querySelector('[data-reset-calculation-simulator]').addEventListener('click',()=>{const isPut=!modal.querySelector('[data-calculation-panel="put"]').hidden;(isPut?$('putCalculationSimulatorForm'):$('calculationSimulatorForm')).reset();if(isPut){$('putCalcAsset').value='';calculatePut();$('putCalcAsset').focus()}else{$('calcAsset').value='';calculateCall();$('calcAsset').focus()}});
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!modal.hidden)close()});calculateCall();calculatePut();
})();
