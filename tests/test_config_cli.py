import contextlib
import io
import json
import os
import tempfile
import unittest

from apismoke.cli import main
from apismoke.config import ConfigError, expand_env, load_config, validate
from server import TestServer


def write(directory, payload, name="checks.json"):
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(payload if isinstance(payload, str) else json.dumps(payload))
    return path


def invoke(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class ConfigTests(unittest.TestCase):
    def test_defaults_applied(self):
        cfg = validate({"checks": [{"name": "a", "path": "/x"}]})
        self.assertEqual(cfg["checks"][0]["method"], "GET")
        self.assertEqual(cfg["checks"][0]["expect"], {"status": 200})

    def test_rejects_bad_configs(self):
        bad = [[], {"checks": []}, {"checks": [{"path": "/"}]}, {"checks": [{"name": "a"}]},
               {"checks": [{"name": "a", "path": "/", "method": "FETCH"}]},
               {"checks": [{"name": "a", "path": "/"}, {"name": "a", "path": "/"}]}]
        for cfg in bad:
            with self.assertRaises(ConfigError, msg=cfg):
                validate(cfg)

    def test_env_expansion(self):
        os.environ["APISMOKE_TEST_TOKEN"] = "abc"
        self.assertEqual(expand_env({"h": ["Bearer ${APISMOKE_TEST_TOKEN}"]}), {"h": ["Bearer abc"]})

    def test_missing_env_var(self):
        os.environ.pop("APISMOKE_NOPE", None)
        with self.assertRaises(ConfigError):
            expand_env("${APISMOKE_NOPE}")

    def test_unreadable_and_invalid_files(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ConfigError):
                load_config(os.path.join(d, "missing.json"))
            with self.assertRaises(ConfigError):
                load_config(write(d, "{not json"))


class CliTests(unittest.TestCase):
    def test_end_to_end_pass_and_fail(self):
        with TestServer() as srv, tempfile.TemporaryDirectory() as d:
            good = write(d, {"base_url": srv.url, "checks": [
                {"name": "health", "path": "/health", "expect": {"json": {"status": "ok"}}}]})
            code, out, _ = invoke("run", good)
            self.assertEqual(code, 0)
            self.assertIn("PASS  health", out)

            bad = write(d, {"base_url": srv.url, "checks": [
                {"name": "health", "path": "/health", "expect": {"json": {"status": "down"}}}]}, "bad.json")
            code, out, _ = invoke("run", bad)
            self.assertEqual(code, 1)
            self.assertIn("FAIL  health", out)

    def test_json_format_and_base_url_override(self):
        with TestServer() as srv, tempfile.TemporaryDirectory() as d:
            cfg = write(d, {"base_url": "http://127.0.0.1:1", "checks": [{"name": "h", "path": "/health"}]})
            code, out, _ = invoke("run", cfg, "--base-url", srv.url, "--format", "json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["passed"], 1)

    def test_config_error_exit_code(self):
        code, _, err = invoke("run", "/no/such/file.json")
        self.assertEqual(code, 2)
        self.assertIn("config error", err)


if __name__ == "__main__":
    unittest.main()
