import re

import pytest

from persona import GREETINGS


@pytest.mark.parametrize("greeting", GREETINGS)
def test_greeting_says_it_is_an_ai(greeting: str) -> None:
    # Every greeting must disclose the AI (ADR-8, I6), so an edit can't drop it.
    assert re.search(r"\bAI\b", greeting)


@pytest.mark.parametrize("greeting", GREETINGS)
def test_greeting_names_lee(greeting: str) -> None:
    assert re.search(r"\bLee\b", greeting)
