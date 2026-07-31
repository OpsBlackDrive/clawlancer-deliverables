#!/usr/bin/env python3
"""Check a Base wallet's native USDC balance through JSON-RPC."""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.request
from decimal import Decimal
from typing import Any

DEFAULT_RPC = "https://mainnet.base.org"
USDC_CONTRACT = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
BALANCE_OF_SELECTOR = "70a08231"


def validate_address(address: str) -> str:
    if not ADDRESS_RE.fullmatch(address):
        raise ValueError("address must be a 20-byte 0x-prefixed hexadecimal value")
    return address


def encode_balance_of(address: str) -> str:
    validate_address(address)
    return "0x" + BALANCE_OF_SELECTOR + address[2:].lower().rjust(64, "0")


def rpc_request(rpc_url: str, method: str, params: list[Any], timeout: float = 15) -> Any:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    request = urllib.request.Request(
        rpc_url,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "base-usdc-balance-checker/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"RPC request failed: {exc}") from exc

    if "error" in payload:
        raise RuntimeError(f"RPC error: {payload['error']}")
    if "result" not in payload:
        raise RuntimeError("RPC response did not include a result")
    return payload["result"]


def get_usdc_balance(address: str, rpc_url: str = DEFAULT_RPC) -> Decimal:
    call = {"to": USDC_CONTRACT, "data": encode_balance_of(address)}
    raw = rpc_request(rpc_url, "eth_call", [call, "latest"])
    if not isinstance(raw, str) or not raw.startswith("0x"):
        raise RuntimeError("RPC returned an invalid balance value")
    return Decimal(int(raw, 16)) / Decimal(1_000_000)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check native USDC balance on Base")
    parser.add_argument("address", help="Base wallet address")
    parser.add_argument("--rpc", default=os.getenv("BASE_RPC_URL", DEFAULT_RPC), help="Base JSON-RPC URL")
    args = parser.parse_args()

    try:
        balance = get_usdc_balance(args.address, args.rpc)
    except (ValueError, RuntimeError) as exc:
        parser.exit(1, f"error: {exc}\n")

    print(f"{args.address}: {balance:f} USDC")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
