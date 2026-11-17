import unittest

from fastapi.testclient import TestClient

from app.main import app


class CorsTests(unittest.TestCase):
    def test_local_dev_origin_is_allowed(self):
        response = TestClient(app).get("/health", headers={"Origin": "http://localhost:5173"})

        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://localhost:5173")

    def test_untrusted_origin_cannot_read_api_response(self):
        response = TestClient(app).get("/health", headers={"Origin": "https://attacker.example"})

        self.assertNotIn("access-control-allow-origin", response.headers)


if __name__ == "__main__":
    unittest.main()
