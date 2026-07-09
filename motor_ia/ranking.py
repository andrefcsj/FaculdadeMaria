def ordenar(itens):
    return sorted(itens,key=lambda x:x.get("score",0),reverse=True)
