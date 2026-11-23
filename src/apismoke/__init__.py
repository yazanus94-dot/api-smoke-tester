"""api-smoke-tester: declarative HTTP API smoke tests with zero dependencies."""
from .config import ConfigError, load_config
from .runner import CheckResult, run_all, run_check

__all__ = ["CheckResult", "ConfigError", "load_config", "run_all", "run_check"]
__version__ = "0.1.0"
