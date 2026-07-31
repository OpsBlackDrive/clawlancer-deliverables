#!/usr/bin/env python3
"""Fetch ETH/USD from three public APIs and return a median price."""

from __future__ import annotations

import json
import statistics
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class Feed:
    name: str
    url: str
    parser: Callable[[dict[str, Any]], Decimal]


@dataclass(frozen=True)
class FeedResult:
    name: str
    price_usd: str | None
    error: str | None


def _positive_decimal(value: Any) -> Decimal:
    try:
        price = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"invalid numeric price: {value!r}") from exc
    if not price.is_finite() or price <= 0:
        raise ValueError(f"price must be positive and finite: {value!r}")
    return price


def parse_coinbase(payload: dict[str, Any]) -> Decimal:
    return _positive_decimal(payload["data"]["amount"])


def parse_coingecko(payload: dict[str, Any]) -> Decimal:
    return _positive_decimal(payload["ethereum"]["usd"])


def parse_kraken(payload: dict[str, Any]) -> Decimal:
    errors = payload.get("error") or []
    if errors:
        raise ValueError(f"Kraken returned errors: {errors}")
    result = payload["result"]
    first_pair = next(iter(result.values()))
    return _positive_decimal(first_pair["c"][0])


FEEDS = (
    Feed("coinbase", "https://api.coinbase.com/v2/prices/ETH-USD/spot", parse_coinbase),
    Feed("coingecko", "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd", parse_coingecko),
    Feed("kraken", "https://api.kraken.com/0/public/Ticker?pair=ETHUSD", parse_kraken),
)


def fetch_json(url: str, *, timeout: float = TIMEOUT_SECONDS) -> dict[str, Any]:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "eth-price-median/1.0"})
    with urlopen(request, timeout=timeout) as response:
        if response.status < 200 or response.status >= 300:
            raise RuntimeError(f"HTTP {response.status}")
        content_type = response.headers.get("Content-Type", "")
        if "json" not in content_type.lower():
            raise RuntimeError(f"unexpected content type: {content_type or 'missing'}")
        raw = response.read(1_000_001)
        if len(raw) > 1_000_000:
            raise RuntimeError("response exceeded 1 MB")
    parsed = json.loads(raw.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise RuntimeError("response JSON must be an object")
    return parsed


def aggregate_eth_price(
    *,
    fetcher: Callable[[str], dict[str, Any]] = fetch_json,
    feeds: tuple[Feed, ...] = FEEDS,
    minimum_successes: int = 2,
) -> dict[str, Any]:
    """Return the median ETH/USD price and per-feed diagnostic results."""
    if not 1 <= minimum_successes <= len(feeds):
        raise ValueError("minimum_successes must be between 1 and the number of feeds")

    prices: list[Decimal] = []
    results: list[FeedResult] = []

    for feed in feeds:
        try:
            price = feed.parser(fetcher(feed.url))
            prices.append(price)
            results.append(FeedResult(feed.name, format(price, "f"), None))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, KeyError, StopIteration, ValueError, RuntimeError) as exc:
            results.append(FeedResult(feed.name, None, f"{type(exc).__name__}: {exc}"))

    if len(prices) < minimum_successes:
        failures = "; ".join(f"{result.name}: {result.error}" for result in results if result.error)
        raise RuntimeError(
            f"only {len(prices)} of {len(feeds)} feeds succeeded; "
            f"need at least {minimum_successes}. {failures}"
        )

    median = statistics.median(prices)
    return {
        "symbol": "ETH/USD",
        "median_price_usd": format(median, "f"),
        "successful_feeds": len(prices),
        "total_feeds": len(feeds),
        "feeds": [asdict(result) for result in results],
    }


def main() -> int:
    try:
        result = aggregate_eth_price()
    except RuntimeError as exc:
        print(json.dumps({"success": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 1
    print(json.dumps({"success": True, **result}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
