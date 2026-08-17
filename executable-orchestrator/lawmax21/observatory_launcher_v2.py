"""Final launcher entrypoint with the protocol-wide preflight installed."""
from . import observatory_launcher as base
from . import observatory_preflight_v4

base.observatory_preflight = observatory_preflight_v4
main = base.main

__all__ = ["main"]
