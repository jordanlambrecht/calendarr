# tests/test_domain.py
"""Event identity and premiere detection."""

import pytest

from conftest import aware, mk_event


class TestPremiereDetection:
    @pytest.mark.parametrize(
        "summary,expected",
        [
            ("Show - S02E01 - Opener", True),
            ("Show - 3x01", True),
            ("Show - S02E11", False),
            ("Show - S02E010", False),
            ("Movie Title (2026)", False),
        ],
    )
    def test_pattern(self, summary, expected):
        assert mk_event(summary, aware(2026, 8, 24)).is_premiere is expected


class TestDedupKey:
    def test_same_summary_same_date(self):
        a = mk_event("Show - S01E01", aware(2026, 8, 24, 9))
        b = mk_event("Show - S01E01", aware(2026, 8, 24, 20))
        assert a.key == b.key

    def test_different_date(self):
        a = mk_event("Show - S01E01", aware(2026, 8, 24))
        b = mk_event("Show - S01E01", aware(2026, 8, 25))
        assert a.key != b.key
