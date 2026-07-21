"""Estimativa explicável de exercício baseada em volatilidade histórica observada."""
from __future__ import annotations
import json, math, statistics, time, urllib.request
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable

@dataclass(frozen=True, slots=True)
class ExerciseProbabilityEstimate:
    probability: Decimal | None
    label: str
    confidence: str
    methodology: str
    annual_volatility: Decimal | None = None
    spot_price: Decimal | None = None
    @property
    def percentage(self) -> str:
        return "--" if self.probability is None else f"{(self.probability*Decimal('100')).quantize(Decimal('0.1'))}%".replace('.', ',')

_CACHE={}; _CACHE_SECONDS=1800; _FAILURE_UNTIL={}

def _normal_cdf(value: float)->float: return .5*(1+math.erf(value/math.sqrt(2)))

def annualized_historical_volatility(closes: Iterable[Decimal])->Decimal|None:
    values=[float(v) for v in closes if v is not None and v>0]
    if len(values)<30:return None
    returns=[math.log(values[i]/values[i-1]) for i in range(1,len(values))]
    if len(returns)<2:return None
    vol=statistics.stdev(returns)*math.sqrt(252)
    return Decimal(str(vol)) if math.isfinite(vol) and vol>0 else None

def estimate_exercise_probability(*,option_type:str,spot_price:Decimal,strike:Decimal,days_to_expiry:int,annual_volatility:Decimal)->ExerciseProbabilityEstimate:
    if spot_price<=0 or strike<=0 or (days_to_expiry>0 and annual_volatility<=0): raise ValueError('Dados inválidos para estimativa.')
    if days_to_expiry<=0:
        p=Decimal('1') if ((option_type.upper()=='PUT' and spot_price<strike) or (option_type.upper()!='PUT' and spot_price>strike)) else Decimal('0') if spot_price!=strike else Decimal('.5')
    else:
        years=days_to_expiry/365; sigma=float(annual_volatility)
        z=(math.log(float(strike/spot_price))+.5*sigma*sigma*years)/(sigma*math.sqrt(years))
        put=_normal_cdf(z); raw=put if option_type.upper()=='PUT' else 1-put
        p=Decimal(str(min(max(raw,0),1)))
    label='Alta' if p>=Decimal('.65') else 'Moderada' if p>=Decimal('.35') else 'Baixa'
    return ExerciseProbabilityEstimate(p,label,'Estatística','Estimativa com volatilidade histórica anualizada e modelo lognormal; não é garantia de exercício.',annual_volatility,spot_price)

def _fetch_yahoo_history(ticker:str):
    now=time.time(); cached=_CACHE.get(ticker)
    if cached and now-cached[0]<_CACHE_SECONDS:return cached[1]
    if _FAILURE_UNTIL.get(ticker,0)>now:raise ValueError('Fonte temporariamente indisponível.')
    symbol=ticker if ticker.endswith('.SA') else f'{ticker}.SA'
    req=urllib.request.Request(f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=6mo&interval=1d',headers={'User-Agent':'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req,timeout=2) as response: payload=json.loads(response.read().decode())
    except Exception:
        _FAILURE_UNTIL[ticker]=now+90
        raise
    results=payload.get('chart',{}).get('result',[])
    if not results: raise ValueError('Histórico indisponível.')
    result=results[0]; meta=result.get('meta',{}); raw=result.get('indicators',{}).get('quote',[{}])[0].get('close',[])
    closes=tuple(Decimal(str(v)) for v in raw if v not in (None,0)); price=meta.get('regularMarketPrice')
    spot=Decimal(str(price)) if price not in (None,0) else (closes[-1] if closes else None)
    out=(spot,closes); _CACHE[ticker]=(now,out); return out

def estimate_operation_exercise_probability(*,ticker:str,option_type:str,strike:Decimal,expiry:date|None,as_of:date|None=None)->ExerciseProbabilityEstimate:
    as_of=as_of or date.today()
    if not ticker or expiry is None or strike<=0:return ExerciseProbabilityEstimate(None,'Indisponível','Dados insuficientes','Cotação, strike ou vencimento ausente.')
    try:
        spot,closes=_fetch_yahoo_history(ticker); vol=annualized_historical_volatility(closes)
        if spot is None or vol is None:return ExerciseProbabilityEstimate(None,'Indisponível','Dados insuficientes','Histórico insuficiente; nenhuma volatilidade foi inventada.',spot_price=spot)
        return estimate_exercise_probability(option_type=option_type,spot_price=spot,strike=strike,days_to_expiry=max((expiry-as_of).days,0),annual_volatility=vol)
    except Exception:
        return ExerciseProbabilityEstimate(None,'Indisponível','Fonte indisponível','Não foi possível obter histórico suficiente; nenhuma probabilidade foi inventada.')
