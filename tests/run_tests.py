#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pytest>=7.0.0",
#     "requests>=2.28.0",
#     "urllib3>=2.0.0",
#     "jsonschema>=4.0.0",
# ]
# ///

"""
Command-Line Test Runner for PubChem Database Visualize Skill
Executes unit, integration, and dashboard tests, returning standard exit codes.
"""

from __future__ import annotations

import sys
from pathlib import Path
import pytest

TEST_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TEST_DIR.parent


def main() -> int:
    print("================================================================================")
    print("RUNNING PUBCHEM DATABASE VISUALIZE TEST SUITE")
    print(f"Test Directory: {TEST_DIR}")
    print("================================================================================")

    pytest_args = [
        str(TEST_DIR),
        "-v",
        "--tb=short",
    ]

    # Pass additional CLI arguments if provided
    if len(sys.argv) > 1:
        pytest_args.extend(sys.argv[1:])

    exit_code = pytest.main(pytest_args)

    print("================================================================================")
    if exit_code == 0:
        print("ALL TESTS PASSED SUCCESSFULLY (Exit Code 0)")
    else:
        print(f"TEST SUITE FAILED WITH EXIT CODE: {exit_code}")
    print("================================================================================")

    return int(exit_code)


if __name__ == "__main__":
    sys.exit(main())
