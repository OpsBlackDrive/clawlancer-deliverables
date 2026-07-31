import unittest

from transaction_formatter import format_transactions, normalize_transaction


class TransactionFormatterTests(unittest.TestCase):
    def test_formats_aliases_and_escapes_markdown(self):
        table = format_transactions(
            [
                {
                    "time": "2026-07-31T00:00:00Z",
                    "hash": "0x1234567890abcdef1234567890abcdef",
                    "chain": "Base",
                    "sender": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "recipient": "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                    "value": "1.230000",
                    "symbol": "USDC|Base",
                    "state": "confirmed",
                }
            ]
        )
        self.assertIn("2026-07-31T00:00:00Z", table)
        self.assertIn("1.23", table)
        self.assertIn("USDC\\|Base", table)
        self.assertIn("0x12345678…90abcdef", table)

    def test_unix_milliseconds_are_converted_to_utc(self):
        row = normalize_transaction({"timestamp": 1_785_456_000_000})
        self.assertTrue(row["timestamp"].endswith("Z"))

    def test_empty_input_has_placeholder_row(self):
        lines = format_transactions([]).splitlines()
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[2].count("—"), 8)

    def test_non_mapping_is_rejected(self):
        with self.assertRaises(TypeError):
            normalize_transaction("not-a-transaction")


if __name__ == "__main__":
    unittest.main()
