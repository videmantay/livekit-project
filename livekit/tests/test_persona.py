import re

import pytest

from persona import GREETINGS, SPANISH_GREETINGS


@pytest.mark.parametrize("greeting", GREETINGS)
def test_greeting_says_it_is_an_ai(greeting: str) -> None:
    # Every greeting must disclose the AI (ADR-8, I6), so an edit can't drop it.
    assert re.search(r"\bAI\b", greeting)


@pytest.mark.parametrize("greeting", SPANISH_GREETINGS)
def test_spanish_greeting_says_it_is_an_ai(greeting: str) -> None:
    assert re.search(r"\bIA\b", greeting)


@pytest.mark.parametrize("greeting", GREETINGS + SPANISH_GREETINGS)
def test_greeting_names_lee(greeting: str) -> None:
    assert re.search(r"\bLee\b", greeting)
