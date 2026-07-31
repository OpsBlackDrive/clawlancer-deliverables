import unittest
from decimal import Decimal

from eth_price_aggregator import FEEDS, aggregate_eth_price


class PriceAggregatorTests(unittest.TestCase):
    def test_returns_median_of_three_feeds(self):
        payloads = {
            FEEDS[0].url: {"data": {"amount": "3010"}},
            FEEDS[1].url: {"ethereum": {"usd": 3000}},
            FEEDS[2].url: {"error": [], "result": {"XETHZUSD": {"c": ["3020", "1"]}}},
        }
        result = aggregate_eth_price(fetcher=payloads.__getitem__)
        self.assertEqual(result["median_price_usd"], "3010")
        self.assertEqual(result["successful_feeds"], 3)

    def test_one_failed_feed_still_returns_median(self):
        def fetcher(url):
            if url == FEEDS[1].url:
                raise TimeoutError("slow")
            return {
                FEEDS[0].url: {"data": {"amount": "3000"}},
                FEEDS[2].url: {"error": [], "result": {"ETHUSD": {"c": ["3020", "1"]}}},
            }[url]

        result = aggregate_eth_price(fetcher=fetcher)
        self.assertEqual(Decimal(result["median_price_usd"]), Decimal("3010"))
        self.assertEqual(result["successful_feeds"], 2)
        self.assertIn("TimeoutError", result["feeds"][1]["error"])

    def test_fewer_than_two_successes_fails(self):
        def fetcher(url):
            if url == FEEDS[0].url:
                return {"data": {"amount": "3000"}}
            raise TimeoutError("down")

        with self.assertRaisesRegex(RuntimeError, "only 1 of 3 feeds succeeded"):
            aggregate_eth_price(fetcher=fetcher)

    def test_non_positive_price_is_rejected(self):
        payloads = {
            FEEDS[0].url: {"data": {"amount": "0"}},
            FEEDS[1].url: {"ethereum": {"usd": -1}},
            FEEDS[2].url: {"error": [], "result": {"ETHUSD": {"c": ["3000", "1"]}}},
        }
        with self.assertRaises(RuntimeError):
            aggregate_eth_price(fetcher=payloads.__getitem__)


if __name__ == "__main__":
    unittest.main()
