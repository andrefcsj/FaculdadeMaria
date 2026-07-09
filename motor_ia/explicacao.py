def explicar(metricas,resultado):
    motivos=[]
    for k,v in metricas.items():
        if v>=0.8: motivos.append(f"{k.title()} favorável")
    return {"score":resultado["score"],"classe":resultado["classe"],"motivos":motivos}
