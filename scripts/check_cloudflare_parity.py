"""Offline parity checks: original Python financial rules vs migrated JS rules."""
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
import json, subprocess, sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine import OptionOpportunity, PutMetricAssumptions, calculate_put_metrics, SafetyFilterConfig, evaluate_put_safety, AssetQualityProfile, assess_asset_quality, evaluate_put_strategy, calculate_put_score
from services.exercise_probability_service import estimate_exercise_probability
from services.closed_operations_service import build_darf_projection
as_of=date(2026,10,8)
fixtures=[]
for premium in ('1.1','2','0'):
 for quality in ('0.88','0.68',None):
  for bid,ask in [('1','1.15'),(None,None)]:
   o=OptionOpportunity(asset='BBAS3',option_code='BBASW270',option_type='PUT',expiry=date(2026,11,20),spot_price=Decimal('28.5'),strike=Decimal('27'),premium=Decimal(premium),bid=Decimal(bid) if bid else None,ask=Decimal(ask) if ask else None,liquidity=Decimal('32000'),timestamp=datetime(2026,10,8,tzinfo=timezone.utc),source='fixture',data_confidence=Decimal('.95'))
   p=AssetQualityProfile(asset='BBAS3',assignment_eligible=True,long_term_suitable=True,quality_score=Decimal(quality) if quality else None,data_confidence=Decimal('.90'))
   m=calculate_put_metrics(o,PutMetricAssumptions(as_of_date=as_of,contract_size=100))
   safety=evaluate_put_safety(o,m,SafetyFilterConfig(min_liquidity=Decimal('10000'),max_spread_pct=Decimal('.25'),min_gross_roi=Decimal('.04'),min_days_to_expiry=15,max_days_to_expiry=60))
   strategy=evaluate_put_strategy(o,m,safety,assess_asset_quality(p));score=calculate_put_score(strategy,m,assess_asset_quality(p))
   fixtures.append({'option':{'asset':o.asset,'option_code':o.option_code,'option_type':o.option_type,'expiry':str(o.expiry),'spot_price':str(o.spot_price),'strike':str(o.strike),'premium':str(o.premium),'bid':bid,'ask':ask,'liquidity':str(o.liquidity),'timestamp':'2026-10-08','source':'fixture'},'profile':{'assignment_eligible':True,'long_term_suitable':True,'quality_score':quality,'data_confidence':'.90'},'expected':{'net_price':float(m.net_acquisition_price),'roi':float(m.gross_roi),'discount':float(m.discount_to_market),'dte':m.days_to_expiry,'status':strategy.status,'score':score.score_int if strategy.status in ['eligible','watchlist'] else None}})
probabilities=[]
for kind in ('PUT','CALL'):
 for spot in (20,25,30):
  p=estimate_exercise_probability(option_type=kind,spot_price=Decimal(spot),strike=Decimal(25),days_to_expiry=30,annual_volatility=Decimal('.3'))
  probabilities.append({'type':kind,'spot':spot,'strike':25,'days':30,'vol':.3,'expected':float(p.probability)})
closed=[{'Ativo':'TEST','Tipo':'PUT','Estrategia':'Venda','Data_abertura':'2026-08-01','Data_fechamento':'2026-08-05','Resultado_realizado':'-100','IRRF':'0','Metodo_encerramento':'recompra'}, {'Ativo':'TEST','Tipo':'PUT','Estrategia':'Venda','Data_abertura':'2026-09-01','Data_fechamento':'2026-09-05','Resultado_realizado':'140','IRRF':'1','Metodo_encerramento':'recompra'}, {'Ativo':'TEST','Tipo':'PUT','Estrategia':'Venda','Data_abertura':'2026-10-01','Data_fechamento':'2026-10-01','Resultado_realizado':'100','IRRF':'1','Metodo_encerramento':'recompra'}]
rows=build_darf_projection(closed,today=as_of)['rows']
fixture={'asOf':str(as_of),'metrics':fixtures,'probabilities':probabilities,'closed':closed,'tax_rows':[{k:float(v) if isinstance(v,Decimal) else v for k,v in row.items() if k in ['competence','common_loss_carry','day_loss_carry','common_taxable_base','day_taxable_base','irrf_deducted','tax_calculated','estimated_darf','tax_carry']} for row in rows]}
js="""const D=require('./static/free-pilot/domain.js'),assert=require('node:assert/strict');let raw='';process.stdin.on('data',x=>raw+=x);process.stdin.on('end',()=>{const f=JSON.parse(raw);for(const x of f.metrics){const r=D.assess(x.option,x.profile,{},f.asOf);for(const k of ['net_price','roi','discount','dte'])assert.ok(Math.abs(r.metrics[k]-x.expected[k])<1e-9,k);assert.equal(r.status,x.expected.status);assert.equal(r.score,x.expected.score);}for(const p of f.probabilities)assert.ok(Math.abs(D.probability(p.type,p.spot,p.strike,p.days,p.vol)-p.expected)<1e-6);const rows=D.taxProjection(f.closed,[],f.asOf);for(const row of f.tax_rows){const r=rows.find(x=>x.competence===row.competence);for(const [k,v]of Object.entries(row))if(k!=='competence')assert.ok(Math.abs(r[k]-v)<1e-6,k);}console.log('PASS parity: '+f.metrics.length+' metrics/score cases, '+f.probabilities.length+' probabilities, '+f.tax_rows.length+' fiscal months.');});"""
subprocess.run(['node','-e',js],input=json.dumps(fixture),text=True,check=True)
