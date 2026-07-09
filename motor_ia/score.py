def calcular_score(metricas):
    return max(0,min(100,sum(metricas.values()) if metricas else 0))
