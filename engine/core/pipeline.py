from ..version import ENGINE_VERSION as V
from .context import DecisionContext as C
PIPELINE_VERSION="sprint-1.1-r"
def run_pipeline(xs,metadata=None):
 x=list(map(dict,xs));c=C(x,metadata or {});t=c.telemetry;n=len(x)
 t.record_event("start");t.record_metric("candidates",n)
 with t.span("run"): y=list(map(dict,x))
 t.record_event("end");m={**c.metadata,"pipeline_version":PIPELINE_VERSION,"engine_version":V,"candidate_count":n,"telemetry":t.summary()}
 return {"candidates":y,"metadata":m}
