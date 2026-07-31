import unittest
from decimal import Decimal
from unittest.mock import patch

from base_usdc_balance import encode_balance_of, get_usdc_balance, validate_address


ADDRESS = "0xd134401b81aa49f39b6f683516a9afd2ff93dc03"


class BalanceCheckerTests(unittest.TestCase):
    def test_validates_address(self) -> None:
        self.assertEqual(validate_address(ADDRESS), ADDRESS)
        with self.assertRaises(ValueError):
            validate_address("0x123")

    def test_encodes_balance_of_call(self) -> None:
        encoded = encode_balance_of(ADDRESS)
        self.assertTrue(encoded.startswith("0x70a08231"))
        self.assertEqual(len(encoded), 2 + 8 + 64)
        self.assertTrue(encoded.endswith(ADDRESS[2:].lower()))

    @patch("base_usdc_balance.rpc_request", return_value=hex(12_345_678))
    def test_converts_six_decimal_usdc(self, mock_rpc) -> None:
        balance = get_usdc_balance(ADDRESS)
        self.assertEqual(balance, Decimal("12.345678"))
        mock_rpc.assert_called_once()

    @patch("base_usdc_balance.rpc_request", return_value="invalid")
    def test_rejects_invalid_rpc_result(self, _mock_rpc) -> None:
        with self.assertRaises(RuntimeError):
            get_usdc_balance(ADDRESS)


if __name__ == "__main__":
    unittest.main()
