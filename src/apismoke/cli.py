"""Command line interface: ``apismoke run checks.json``."""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .config import ConfigError, load_config
from .runner import run_all


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="apismoke", description="Declarative HTTP API smoke tests.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run every check in a JSON file")
    run.add_argument("config", help="path to the JSON check file")
    run.add_argument("--base-url", default="", help="override base_url from the file")
    run.add_argument("--timeout", type=float, default=10.0, help="per-request timeout in seconds")
    run.add_argument("--format", choices=["text", "json"], default="text")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2

    results = run_all(config, args.timeout, args.base_url)
    failed = [r for r in results if not r.passed]

    if args.format == "json":
        print(json.dumps({"passed": len(results) - len(failed), "failed": len(failed),
                          "results": [r.as_dict() for r in results]}, indent=2))
    else:
        for r in results:
            print(f"{'PASS' if r.passed else 'FAIL'}  {r.name}  [{r.status or '-'}] {r.elapsed_ms:.0f} ms")
            for failure in r.failures:
                print(f"      - {failure}")
        print(f"\n{len(results) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
