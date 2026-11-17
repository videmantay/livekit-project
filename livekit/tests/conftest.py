import pytest

from config import AgentSettings, FactsSettings


@pytest.fixture(autouse=True)
def hermetic_env(monkeypatch):
    # Real config from the shell must never reach the tests. Tests that need a value set it.
    # LEE_LEGAL_NAME is left alone: test_facts opts into it to check the prompt.
    for model in (FactsSettings, AgentSettings):
        for name in model.model_fields:
            monkeypatch.delenv(name.upper(), raising=False)
