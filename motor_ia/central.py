from .configuracao import PESOS
from .score import calcular_score
from .ranking import ordenar_oportunidades

class MotorIA:
    def analisar(self,oportunidades):
        itens=[]
        for op in oportunidades:
            op=dict(op)
            op["score"]=calcular_score(op,PESOS)
            itens.append(op)
        return ordenar_oportunidades(itens)
