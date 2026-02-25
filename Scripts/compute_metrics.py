# shim to make "Scripts.compute_metrics" import the real module under "scripts"
import importlib as _importlib
_real = _importlib.import_module("scripts.compute_metrics")
try:
    __all__ = _real.__all__
except AttributeError:
    __all__ = [n for n in dir(_real) if not n.startswith("_")]
globals().update({name: getattr(_real, name) for name in __all__})
