"""Called manually by a VW Python MENU COMMAND; not a timer/socket callback."""
from .transport import Pump
from .vw_adapter import VwAdapter
from .wire import read_config

_runtime = None
_config_path = None


def run_once(config_path):
    global _runtime, _config_path
    if _runtime is None:
        import vs
        config, key = read_config(config_path)
        _runtime = Pump(config, key, VwAdapter(vs))
        _config_path = config_path
    if config_path != _config_path:
        raise RuntimeError('Restart VW before changing the test configuration')
    return _runtime.run_once()
