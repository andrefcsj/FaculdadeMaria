import unittest

from app import app


class NotificationCenterTests(unittest.TestCase):
    def test_alerts_endpoint_returns_expected_shape(self):
        response = app.test_client().get("/api/alertas-operacionais")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("count", payload)
        self.assertIn("items", payload)
        self.assertEqual(payload["count"], len(payload["items"]))

    def test_topbar_has_accessible_notification_center(self):
        html = app.test_client().get("/").get_data(as_text=True)
        self.assertIn('id="notificationBell"', html)
        self.assertIn('id="notificationPopover"', html)
        self.assertIn("/api/alertas-operacionais", open("static/theme.js", encoding="utf-8").read())


if __name__ == "__main__":
    unittest.main()
