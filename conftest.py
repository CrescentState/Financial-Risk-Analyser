import os
import importlib
import pytest


@pytest.fixture(scope="session", autouse=True)
def _enable_test_mode():
    """Enable mock/test data across the suite.

    The `env` section in pytest.ini is a no-op without the pytest-env plugin,
    so this fixture sets USE_MOCK_DATA and toggles each agent's
    _TEST_MODE_OVERRIDE flag directly. Tests bypass network calls for data
    fetching; agents that call Gemini are patched per-test as needed.
    """
    os.environ.setdefault("USE_MOCK_DATA", "true")
    for module_name in (
        "agents.financial_agent",
        "agents.news_agent",
        "agents.risk_agent",
        "agents.synthesis_agent",
        "core.resolver",
    ):
        module = importlib.import_module(module_name)
        module._TEST_MODE_OVERRIDE = True