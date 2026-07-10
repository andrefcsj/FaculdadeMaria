from ..errors import EngineContractError
from ..version import get_engine_version
from .context import DecisionContext

PIPELINE_VERSION = 'sprint-1.1-r'

class DecisionPipeline:
    def run(self, candidates, metadata=None):
        if not isinstance(candidates, (list, tuple)):
            raise EngineContractError('Candidates must be a list or tuple')
        items = list(candidates)
        ctx = DecisionContext(metadata=dict(metadata or {}))
        ctx.telemetry.record_event('started')
        ctx.telemetry.record_metric('candidates_received', len(items))
        with ctx.telemetry.span('run'):
            ctx.add_trace('pipeline', 'pass_through')
        ctx.telemetry.record_event('finished')
        result_metadata = dict(ctx.metadata)
        result_metadata['pipeline_version'] = PIPELINE_VERSION
        result_metadata['engine_version'] = get_engine_version()
        result_metadata['telemetry'] = ctx.telemetry.summary()
        return {'candidates': items, 'traces': list(ctx.traces), 'metadata': result_metadata}

def run_pipeline(candidates, metadata=None):
    return DecisionPipeline().run(candidates, metadata)
