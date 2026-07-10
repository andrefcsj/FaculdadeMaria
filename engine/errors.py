"""Decision Engine domain errors."""


class DecisionEngineError(Exception):
    default_code = "decision_engine_error"

    def __init__(self, message="Decision Engine error", code=None, details=None):
        super().__init__(message)
        self.code = code or self.default_code
        self.message = message
        self.details = dict(details or {})

    def to_dict(self):
        return {"code": self.code, "message": self.message, "details": dict(self.details)}


class EngineConfigurationError(DecisionEngineError):
    default_code = "engine_configuration_error"


class EngineContractError(DecisionEngineError):
    default_code = "engine_contract_error"


class EnginePipelineError(DecisionEngineError):
    default_code = "engine_pipeline_error"


class EngineProviderError(DecisionEngineError):
    default_code = "engine_provider_error"


class EngineTelemetryError(DecisionEngineError):
    default_code = "engine_telemetry_error"
