import unittest

from validate_agent_profile import is_valid_agent_profile, validate_agent_profile


VALID = {
    "name": "OpsBlackDrive-Earner",
    "bio": "An autonomous agent for coding, research, and documentation tasks.",
    "skills": ["python", "api", "documentation"],
    "wallet_address": "0xd134401b81aa49f39b6f683516a9afd2ff93dc03",
}


class AgentProfileValidatorTests(unittest.TestCase):
    def test_valid_profile(self):
        self.assertTrue(is_valid_agent_profile(VALID))
        self.assertEqual(validate_agent_profile(VALID), [])

    def test_missing_fields_are_stable_and_sorted(self):
        errors = validate_agent_profile({})
        self.assertEqual(
            [error["path"] for error in errors],
            ["$.bio", "$.name", "$.skills", "$.wallet_address"],
        )

    def test_rejects_duplicate_and_bad_skills(self):
        profile = {**VALID, "skills": ["Python", "python", "python"]}
        errors = validate_agent_profile(profile)
        codes = [error["code"] for error in errors]
        self.assertIn("pattern", codes)
        self.assertIn("unique", codes)

    def test_rejects_private_key_shaped_extra_field(self):
        profile = {**VALID, "private_key": "not-allowed"}
        errors = validate_agent_profile(profile)
        self.assertIn(
            {"path": "$.private_key", "code": "additional_property", "message": "field is not allowed"},
            errors,
        )

    def test_rejects_invalid_wallet(self):
        profile = {**VALID, "wallet_address": "0x1234"}
        errors = validate_agent_profile(profile)
        self.assertEqual(errors[0]["path"], "$.wallet_address")
        self.assertEqual(errors[0]["code"], "pattern")


if __name__ == "__main__":
    unittest.main()
