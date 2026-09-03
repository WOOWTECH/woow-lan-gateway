import unittest

from gateway.app import NotificationOutbox


class NotificationContractTest(unittest.TestCase):
    def test_failed_delivery_is_retried_until_home_assistant_is_ready(self):
        attempts = []

        def delivery(state, message):
            attempts.append((state, message))
            return len(attempts) > 1

        outbox = NotificationOutbox(delivery)
        outbox.publish("已啟用", "gateway enabled")

        self.assertTrue(outbox.pending)
        outbox.retry()

        self.assertFalse(outbox.pending)
        self.assertEqual(
            [("已啟用", "gateway enabled"), ("已啟用", "gateway enabled")],
            attempts,
        )


if __name__ == "__main__":
    unittest.main()
