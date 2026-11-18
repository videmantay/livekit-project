import pytest

from facts import GROUNDING_RULES
from languages import LINES, LanguageSwitch, language_rules, start_language


@pytest.mark.parametrize(
    ("metadata", "expected"),
    [
        ({}, "en"),  # a local run, or a dispatch that didn't come from cloud-run
        ({"terms_language": "en"}, "en"),
        ({"terms_language": "es"}, "es"),
        ({"terms_language": "pt"}, "en"),  # never Portuguese (ADR-20)
    ],
)
def test_call_starts_in_the_terms_language(metadata, expected):
    assert start_language(metadata) == expected


@pytest.mark.parametrize("start", ["en", "es"])
def test_rules_allow_both_languages_and_never_portuguese(start):
    rules = language_rules(start)
    assert "English and fluent Spanish" in rules
    assert "set_language" in rules
    assert "Never speak Portuguese" in rules
    assert "gender-neutral" in rules
    assert ("starts in Spanish" in rules) == (start == "es")


def test_no_english_only_rule_is_left():
    for text in (GROUNDING_RULES, language_rules("en")):
        assert "other than English" not in text


def test_switch_changes_the_voice_once():
    voices = []
    switch = LanguageSwitch("en", voices.append)
    assert "Switched to Spanish" in switch.switch("es")
    assert "Already speaking Spanish" in switch.switch("es")
    assert "Switched to English" in switch.switch("en")
    assert voices == ["es", "en"]
    assert switch.current == "en"


def test_every_language_has_every_line():
    for lines in LINES.values():
        assert lines.blocked and lines.no_facts and lines.time_up
    assert "IA" in LINES["es"].no_facts
