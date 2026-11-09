"""Execute checks against a live API and compare the response to expectations."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, List

_MISSING = object()


@dataclass
class CheckResult:
    name: str
    passed: bool
    status: int = 0
    elapsed_ms: float = 0.0
    failures: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"name": self.name, "passed": self.passed, "status": self.status,
                "elapsed_ms": round(self.elapsed_ms, 1), "failures": self.failures}


def lookup(data: Any, path: str) -> Any:
    """Resolve ``a.b.0.c`` against nested dicts/lists. Returns a sentinel when absent."""
    current = data
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.lstrip("-").isdigit() and -len(current) <= int(part) < len(current):
            current = current[int(part)]
        else:
            return _MISSING
    return current


def _fetch(base_url: str, check: dict, timeout: float):
    url = base_url.rstrip("/") + "/" + check["path"].lstrip("/") if base_url else check["path"]
    headers = {str(k): str(v) for k, v in check.get("headers", {}).items()}
    data = None
    if "body" in check:
        data = json.dumps(check["body"]).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=data, headers=headers, method=check["method"])
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            body, status, resp_headers = resp.read(), resp.status, resp.headers
    except urllib.error.HTTPError as exc:  # 4xx/5xx still carry a response we can assert on
        body, status, resp_headers = exc.read(), exc.code, exc.headers
    return status, resp_headers, body, (time.perf_counter() - started) * 1000


def run_check(base_url: str, check: dict, timeout: float = 10.0) -> CheckResult:
    result = CheckResult(check["name"], passed=False)
    try:
        status, headers, body, elapsed = _fetch(base_url, check, timeout)
    except Exception as exc:  # network errors, timeouts, bad URLs
        result.failures.append(f"request failed: {exc}")
        return result

    result.status, result.elapsed_ms = status, elapsed
    expect = check.get("expect", {})
    text = body.decode("utf-8", errors="replace")

    want = expect.get("status", 200)
    allowed = want if isinstance(want, list) else [want]
    if status not in allowed:
        result.failures.append(f"status: expected {want}, got {status}")

    limit = expect.get("max_ms")
    if limit is not None and elapsed > limit:
        result.failures.append(f"latency: {elapsed:.0f} ms exceeds max_ms {limit}")

    for name, fragment in expect.get("headers", {}).items():
        actual = headers.get(name)
        if actual is None:
            result.failures.append(f"header '{name}' is missing")
        elif str(fragment).lower() not in actual.lower():
            result.failures.append(f"header '{name}': expected to contain '{fragment}', got '{actual}'")

    if "body_contains" in expect and expect["body_contains"] not in text:
        result.failures.append(f"body does not contain '{expect['body_contains']}'")

    if "json" in expect or "json_has" in expect:
        try:
            payload = json.loads(text)
        except ValueError:
            result.failures.append("body is not valid JSON")
            payload = _MISSING
        if payload is not _MISSING:
            for path, wanted in expect.get("json", {}).items():
                actual = lookup(payload, path)
                if actual is _MISSING:
                    result.failures.append(f"json '{path}': field not found")
                elif actual != wanted:
                    result.failures.append(f"json '{path}': expected {wanted!r}, got {actual!r}")
            for path in expect.get("json_has", []):
                if lookup(payload, path) is _MISSING:
                    result.failures.append(f"json '{path}': field not found")

    result.passed = not result.failures
    return result


def run_all(config: dict, timeout: float = 10.0, base_url: str = "") -> List[CheckResult]:
    base = base_url or config.get("base_url", "")
    return [run_check(base, check, timeout) for check in config["checks"]]
