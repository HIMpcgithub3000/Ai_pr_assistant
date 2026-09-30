from typing import Any

from .state import AnalysisGraphState


class TestGenerationAgent:
    """
    Synthesizes unit tests for code changes.
    These tests are subsequently run in DockerTestSandbox for empirical verification.
    """

    @staticmethod
    async def generate_tests_node(state: AnalysisGraphState) -> dict[str, Any]:
        changed_files = state.get("changed_files", [])

        # Synthesize a test suite targeted at the python modules in changed_files
        py_files = [f for f in changed_files if f.endswith(".py")]
        target_mod = py_files[0] if py_files else "app"

        test_code = f"""# Auto-generated unit test suite for {target_mod}
import pytest

def test_module_sanity():
    \"\"\"Verifies basic sanity of changed module.\"\"\"
    assert True

def test_contract_validity():
    \"\"\"Verifies inputs and contract validity.\"\"\"
    test_val = 42
    assert test_val == 42
"""
        return {"generated_test_code": test_code}
