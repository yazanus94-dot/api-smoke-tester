import unittest

from apismoke.runner import lookup, run_check, _MISSING
from server import TestServer


class LookupTests(unittest.TestCase):
    def test_nested_dict_and_list(self):
        data = {"a": {"b": [{"c": 5}, {"c": 6}]}}
        self.assertEqual(lookup(data, "a.b.1.c"), 6)

    def test_missing_paths(self):
        data = {"a": [1]}
        self.assertIs(lookup(data, "a.5"), _MISSING)
        self.assertIs(lookup(data, "x"), _MISSING)
        self.assertIs(lookup(data, "a.b"), _MISSING)

    def test_negative_index(self):
        self.assertEqual(lookup({"a": [1, 2, 3]}, "a.-1"), 3)


class RunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = TestServer().__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.server.__exit__(None, None, None)

    def check(self, **kw):
        base = {"name": "t", "method": "GET", "path": "/health", "expect": {"status": 200}}
        base.update(kw)
        return run_check(self.server.url, base, timeout=5)

    def test_passing_check(self):
        r = self.check(expect={"status": 200, "json": {"status": "ok"}, "json_has": ["version"],
                               "headers": {"Content-Type": "application/json"}})
        self.assertTrue(r.passed, r.failures)
        self.assertEqual(r.status, 200)

    def test_status_mismatch(self):
        r = self.check(path="/nope")
        self.assertFalse(r.passed)
        self.assertIn("expected 200, got 404", r.failures[0])

    def test_status_list_allows_404(self):
        self.assertTrue(self.check(path="/nope", expect={"status": [200, 404]}).passed)

    def test_json_value_mismatch_and_missing_field(self):
        r = self.check(expect={"json": {"status": "down", "ghost": 1}})
        self.assertEqual(len(r.failures), 2)

    def test_json_path_into_list(self):
        r = self.check(path="/users", expect={"json": {"items.1.name": "Linus"}})
        self.assertTrue(r.passed, r.failures)

    def test_latency_budget(self):
        self.assertFalse(self.check(path="/slow", expect={"max_ms": 50}).passed)
        self.assertTrue(self.check(path="/slow", expect={"max_ms": 3000}).passed)

    def test_body_contains_and_invalid_json(self):
        self.assertTrue(self.check(path="/text", expect={"body_contains": "plain"}).passed)
        r = self.check(path="/text", expect={"json_has": ["x"]})
        self.assertIn("body is not valid JSON", r.failures)

    def test_missing_header(self):
        r = self.check(expect={"headers": {"X-Request-Id": "abc"}})
        self.assertIn("header 'X-Request-Id' is missing", r.failures)

    def test_post_sends_json_body(self):
        r = self.check(method="POST", path="/users", body={"name": "Grace"},
                       expect={"status": 201, "json": {"echo.name": "Grace", "type": "application/json"}})
        self.assertTrue(r.passed, r.failures)

    def test_custom_headers_sent(self):
        r = self.check(path="/auth", headers={"Authorization": "Bearer secret-token"},
                       expect={"json": {"authorized": True}})
        self.assertTrue(r.passed, r.failures)
        r = self.check(path="/auth", expect={"status": 401})
        self.assertTrue(r.passed, r.failures)

    def test_connection_error_is_reported_not_raised(self):
        r = run_check("http://127.0.0.1:1", {"name": "x", "method": "GET", "path": "/", "expect": {}}, timeout=2)
        self.assertFalse(r.passed)
        self.assertTrue(r.failures[0].startswith("request failed"))


if __name__ == "__main__":
    unittest.main()
