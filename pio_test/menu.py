"""Called manually by a VW Python MENU COMMAND; not a timer/socket callback."""

from .transport import Pump
from .vw_adapter import VwAdapter
from .wire import read_config
from .errors import Rejected, require
from .native_proof import NativeProof
from .operator_control import state

_runtime = None
_config_path = None
_startup_unconfirmed = False


def initialize(config_path):
    global _runtime, _config_path, _startup_unconfirmed
    if _runtime is None:
        import vs

        config, key = read_config(config_path)
        try:
            _runtime = Pump(config, key, VwAdapter(vs))
        except Exception:
            _startup_unconfirmed = True
            raise
        _config_path = config_path
    if config_path != _config_path:
        raise RuntimeError("Restart VW before changing the test configuration")
    return _runtime


def run_once(config_path):
    # Initialization is a separate local operator action, never an MCP side effect.
    require(_runtime is not None, "LOCAL_ENABLE_REQUIRED")
    require(config_path == _config_path, "RESTART_BEFORE_CONFIG_CHANGE")
    return _runtime.run_once()


def operator_sync(config_path):
    """Fixed local Python operator menu; no queued job dispatch or drawing query."""
    import vs

    proof = NativeProof(vs)
    info = vs.GetPluginInfo()
    require(
        type(info) is tuple
        and len(info) == 3
        and info[0]
        and info[1] == "AV PIO Test Operator",
        "NATIVE_MENU_CONTEXT_UNVERIFIED",
    )
    pio = vs.GetCustomObjectInfo()
    require(
        type(pio) is tuple and len(pio) == 5 and not pio[2], "PIO_REENTRANT_CONTEXT"
    )
    native = proof.call("AVPIOTestGate")
    action = native.get("operator_action")
    require(action in ("initialize", "sync", "status"), "LOCAL_OPERATOR_SCOPE_REQUIRED")
    if action == "initialize":
        initialize(config_path)  # starts OFF; native Enable occurs only afterwards
    value = proof.control()
    if _runtime is None:
        status = {
            "state": state(value, uncertain=_startup_unconfirmed),
            "outcome_unconfirmed": _startup_unconfirmed,
        }
    else:
        try:
            status = _runtime.operator_sync()
        except Exception:
            # Native OFF is already decisive even with a broken IPC directory.
            status = _runtime.engine.operator_status()
            if value["enabled"]:
                status["state"] = "UNCONFIRMED"
            status["outcome_unconfirmed"] = True
    if _startup_unconfirmed and value["enabled"]:
        status["state"] = "UNCONFIRMED"
    proof.call(
        "AVPIOTestOperatorReport",
        status["state"] + (";UNCONFIRMED" if status.get("outcome_unconfirmed") else ""),
    )
    return status
