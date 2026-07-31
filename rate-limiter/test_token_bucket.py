import unittest

from token_bucket import TokenBucket


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class TokenBucketTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        self.bucket = TokenBucket(rate=2, burst=3, clock=self.clock)

    def test_allows_initial_burst(self) -> None:
        self.assertTrue(self.bucket.consume().allowed)
        self.assertTrue(self.bucket.consume().allowed)
        decision = self.bucket.consume()
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.remaining_tokens, 0)

    def test_rejects_when_empty_with_retry_time(self) -> None:
        for _ in range(3):
            self.bucket.consume()
        decision = self.bucket.consume()
        self.assertFalse(decision.allowed)
        self.assertAlmostEqual(decision.retry_after_seconds, 0.5)

    def test_refills_using_elapsed_time(self) -> None:
        for _ in range(3):
            self.bucket.consume()
        self.clock.advance(1.0)
        self.assertAlmostEqual(self.bucket.available(), 2.0)

    def test_refill_is_capped_at_burst(self) -> None:
        self.bucket.consume()
        self.clock.advance(100)
        self.assertEqual(self.bucket.available(), 3.0)

    def test_supports_fractional_costs(self) -> None:
        decision = self.bucket.consume(0.5)
        self.assertTrue(decision.allowed)
        self.assertAlmostEqual(decision.remaining_tokens, 2.5)

    def test_validates_configuration_and_cost(self) -> None:
        with self.assertRaises(ValueError):
            TokenBucket(rate=0, burst=1)
        with self.assertRaises(ValueError):
            TokenBucket(rate=1, burst=0)
        with self.assertRaises(ValueError):
            self.bucket.consume(0)
        with self.assertRaises(ValueError):
            self.bucket.consume(4)


if __name__ == "__main__":
    unittest.main()
