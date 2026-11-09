"""api-smoke-tester: declarative HTTP API smoke tests with zero dependencies."""
from .config import ConfigError, load_config
from .runner import CheckResult, run_check, run_all

__all__ = ["ConfigError", "load_config", "CheckResult", "run_check", "run_all"]
__version__ = "0.1.0"
