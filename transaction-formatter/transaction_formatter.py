#!/usr/bin/env python3
"""Format blockchain transactions as a deterministic Markdown table."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

_COLUMNS = (
    ("timestamp", "Timestamp"),
    ("tx_hash", "Transaction"),
    ("network", "Network"),
    ("from", "From"),
    ("to", "To"),
    ("amount", "Amount"),
    ("asset", "Asset"),
    ("status", "Status"),
)


def _escape_markdown(value: Any) -> str:
    if value is None:
        return "—"
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    if not text:
        return "—"
    return text.replace("\\", "\\\\").replace("|", "\\|")


def _shorten(value: Any, *, head: int = 8, tail: int = 6) -> str:
    text = _escape_markdown(value)
    if text == "—" or len(text) <= head + tail + 3:
        return text
    return f"{text[:head]}…{text[-tail:]}"


def _format_timestamp(value: Any) -> str:
    if value in (None, ""):
        return "—"

    if isinstance(value, (int, float)):
        seconds = float(value)
        if seconds > 10_000_000_000:  # milliseconds
            seconds /= 1000
        return datetime.fromtimestamp(seconds, tz=UTC).isoformat().replace("+00:00", "Z")

    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return _escape_markdown(text)

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _format_amount(value: Any) -> str:
    if value in (None, ""):
        return "—"
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return _escape_markdown(value)

    normalized = format(amount.normalize(), "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return normalized or "0"


def _pick(transaction: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in transaction:
            return transaction[key]
    return None


def normalize_transaction(transaction: Mapping[str, Any]) -> dict[str, str]:
    """Normalize common transaction field aliases into display-ready values."""
    if not isinstance(transaction, Mapping):
        raise TypeError("each transaction must be a mapping")

    return {
        "timestamp": _format_timestamp(_pick(transaction, "timestamp", "time", "created_at", "block_time")),
        "tx_hash": _shorten(_pick(transaction, "tx_hash", "hash", "transaction_hash", "id"), head=10, tail=8),
        "network": _escape_markdown(_pick(transaction, "network", "chain", "chain_name")),
        "from": _shorten(_pick(transaction, "from", "from_address", "sender")),
        "to": _shorten(_pick(transaction, "to", "to_address", "recipient")),
        "amount": _format_amount(_pick(transaction, "amount", "value", "quantity")),
        "asset": _escape_markdown(_pick(transaction, "asset", "symbol", "token")),
        "status": _escape_markdown(_pick(transaction, "status", "state", "result")),
    }


def format_transactions(transactions: Iterable[Mapping[str, Any]]) -> str:
    """Return transactions as a Markdown table with stable column ordering."""
    rows = [normalize_transaction(transaction) for transaction in transactions]
    headers = [label for _, label in _COLUMNS]
    separator = ["---"] * len(_COLUMNS)

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row[key] for key, _ in _COLUMNS) + " |")

    if not rows:
        lines.append("| " + " | ".join(["—"] * len(_COLUMNS)) + " |")
    return "\n".join(lines)


def _load_json(path: str | None) -> list[Mapping[str, Any]]:
    raw = Path(path).read_text(encoding="utf-8") if path else __import__("sys").stdin.read()
    parsed = json.loads(raw)
    if isinstance(parsed, Mapping):
        parsed = parsed.get("transactions", parsed.get("data"))
    if not isinstance(parsed, list):
        raise ValueError("input must be a JSON array or an object containing 'transactions'/'data'")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_file", nargs="?", help="JSON file; omit to read stdin")
    args = parser.parse_args()
    try:
        print(format_transactions(_load_json(args.json_file)))
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
