"""Single source of truth for the Decision Engine version."""

ENGINE_VERSION = "1.1.0"
ENGINE_CODENAME = "foundation"


def get_engine_version() -> str:
    return ENGINE_VERSION
