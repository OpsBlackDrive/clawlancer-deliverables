#!/usr/bin/env python3
"""Validate an AI-agent profile against the bundled JSON Schema contract."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.-]*$")
SKILL_RE = re.compile(r"^[a-z0-9][a-z0-9+.#_-]*$")
EVM_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
ALLOWED_FIELDS = {"name", "bio", "skills", "wallet_address"}


def validate_agent_profile(profile: Any) -> list[dict[str, str]]:
    """Return stable-order validation errors; an empty list means valid."""
    errors: list[dict[str, str]] = []

    def add(path: str, code: str, message: str) -> None:
        errors.append({"path": path, "code": code, "message": message})

    if not isinstance(profile, Mapping):
        add("$", "type", "profile must be a JSON object")
        return errors

    for field in sorted(ALLOWED_FIELDS - set(profile)):
        add(f"$.{field}", "required", "field is required")
    for field in sorted(set(profile) - ALLOWED_FIELDS):
        add(f"$.{field}", "additional_property", "field is not allowed")

    name = profile.get("name")
    if name is not None:
        if not isinstance(name, str):
            add("$.name", "type", "name must be a string")
        else:
            if not 2 <= len(name) <= 64:
                add("$.name", "length", "name must contain 2 to 64 characters")
            if name and not NAME_RE.fullmatch(name):
                add("$.name", "pattern", "name contains unsupported characters")

    bio = profile.get("bio")
    if bio is not None:
        if not isinstance(bio, str):
            add("$.bio", "type", "bio must be a string")
        elif not 10 <= len(bio) <= 500:
            add("$.bio", "length", "bio must contain 10 to 500 characters")

    skills = profile.get("skills")
    if skills is not None:
        if not isinstance(skills, list):
            add("$.skills", "type", "skills must be an array")
        else:
            if not 1 <= len(skills) <= 25:
                add("$.skills", "items", "skills must contain 1 to 25 items")
            seen: set[str] = set()
            for index, skill in enumerate(skills):
                path = f"$.skills[{index}]"
                if not isinstance(skill, str):
                    add(path, "type", "skill must be a string")
                    continue
                if not 1 <= len(skill) <= 40:
                    add(path, "length", "skill must contain 1 to 40 characters")
                if skill and not SKILL_RE.fullmatch(skill):
                    add(path, "pattern", "skill must be lowercase and slug-like")
                if skill in seen:
                    add(path, "unique", "skill is duplicated")
                seen.add(skill)

    wallet = profile.get("wallet_address")
    if wallet is not None:
        if not isinstance(wallet, str):
            add("$.wallet_address", "type", "wallet_address must be a string")
        elif not EVM_RE.fullmatch(wallet):
            add("$.wallet_address", "pattern", "wallet_address must be a 20-byte EVM address")

    return errors


def is_valid_agent_profile(profile: Any) -> bool:
    return not validate_agent_profile(profile)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path, help="Path to a JSON agent profile")
    args = parser.parse_args()

    try:
        profile = json.loads(args.profile.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "errors": [{"path": "$", "code": "input", "message": str(exc)}]}, indent=2))
        return 2

    errors = validate_agent_profile(profile)
    print(json.dumps({"valid": not errors, "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
