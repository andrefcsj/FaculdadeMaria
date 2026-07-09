from .configuracao import PESOS

CLASSES=[(90,"Excelente"),(80,"Muito Boa"),(70,"Boa"),(60,"Regular"),(0,"Atenção")]

def calcular_score(metricas):
    total=0
    for k,p in PESOS.items():
        total+=metricas.get(k,0)*p
    score=round(max(0,min(100,total)))
    classe=next(c for lim,c in CLASSES if score>=lim)
    return {"score":score,"classe":classe}
