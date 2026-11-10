# api-smoke-tester

[![CI](https://github.com/yazanus94-dot/api-smoke-tester/actions/workflows/ci.yml/badge.svg)](https://github.com/yazanus94-dot/api-smoke-tester/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Declarative HTTP API smoke tests. Describe your endpoints and expectations in a JSON file, run one command, get a pass/fail report and an exit code your pipeline can trust.

- Zero runtime dependencies, standard library only
- Assert on status codes, response headers, JSON fields (dotted paths, list indexes), body text and latency
- Secrets via `${ENV_VAR}` placeholders, so tokens never live in the repo
- Failures are reported, never raised: network errors and timeouts become readable results
- Text and JSON reports, CI-friendly exit codes

## Install

```bash
git clone https://github.com/yazanus94-dot/api-smoke-tester.git
cd api-smoke-tester
python -m pip install -e .
```

## Quick start

`checks.json`:

```json
{
  "base_url": "https://api.example.com",
  "checks": [
    {
      "name": "health endpoint",
      "path": "/health",
      "expect": { "status": 200, "max_ms": 500, "json": { "status": "ok" } }
    },
    {
      "name": "create a user",
      "method": "POST",
      "path": "/users",
      "headers": { "Authorization": "Bearer ${API_TOKEN}" },
      "body": { "name": "Ada" },
      "expect": {
        "status": [200, 201],
        "headers": { "Content-Type": "application/json" },
        "json": { "name": "Ada" },
        "json_has": ["id"]
      }
    }
  ]
}
```

```bash
API_TOKEN=secret apismoke run checks.json
```

```text
PASS  health endpoint  [200] 84 ms
PASS  create a user  [201] 131 ms

2 passed, 0 failed
```

A failing run explains exactly what differed:

```text
FAIL  health endpoint  [200] 91 ms
      - json 'status': expected 'ok', got 'degraded'
      - latency: 640 ms exceeds max_ms 500

1 passed, 1 failed
```

A ready-made example for the public GitHub API is in `examples/checks.json`.

## Check reference

| Field | Meaning |
|---|---|
| `name` | Unique label (required) |
| `path` | Path appended to `base_url` (required) |
| `method` | `GET` (default), `POST`, `PUT`, `PATCH`, `DELETE`, `HEAD`, `OPTIONS` |
| `headers` | Request headers |
| `body` | JSON request body (sets `Content-Type: application/json`) |
| `expect.status` | Expected status code, or a list of allowed codes (default `200`) |
| `expect.max_ms` | Latency budget in milliseconds |
| `expect.headers` | Header name to a substring it must contain (case-insensitive) |
| `expect.json` | Dotted path to exact expected value, e.g. `"items.0.name": "Ada"` |
| `expect.json_has` | List of dotted paths that must exist |
| `expect.body_contains` | Text the raw body must contain |

### CLI

```text
apismoke run CONFIG [--base-url URL] [--timeout SECONDS] [--format text|json]
```

Exit codes: `0` all checks passed, `1` at least one failed, `2` invalid configuration.

`--base-url` overrides the file, so one check file can run against staging and production.

### GitHub Actions

```yaml
- name: API smoke tests
  run: apismoke run checks.json --base-url "$STAGING_URL"
  env:
    API_TOKEN: ${{ secrets.API_TOKEN }}
    STAGING_URL: ${{ vars.STAGING_URL }}
```

## Development

The test suite starts a local HTTP server, so it needs no network access.

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

## Roadmap

- Response time percentiles over repeated runs
- JUnit XML output for CI test reports
- Request chaining (reuse a value from one response in the next request)

Contributions are welcome, see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE) © Yazan Aljabari
