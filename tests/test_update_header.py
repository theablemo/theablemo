"""Protect public-only counts and retain old assets on incomplete upstream data."""

from datetime import date
import unittest

from scripts.update_header import language_groups, parse_calendar


class PublicDataTests(unittest.TestCase):
    def test_calendar_uses_tooltip_counts_and_ignores_future_dates(self):
        html = '''
        <td id="a" data-date="2026-01-01"></td>
        <tool-tip for="a">1,234 contributions on January 1st.</tool-tip>
        <td id="b" data-date="2026-01-02"></td>
        <tool-tip for="b">No contributions on January 2nd.</tool-tip>
        <td id="c" data-date="2026-01-03"></td>
        <tool-tip for="c">9 contributions on January 3rd.</tool-tip>'''
        self.assertEqual(parse_calendar(html, date(2026, 1, 2)), {"2026-01-01": 1234, "2026-01-02": 0})

    def test_missing_days_are_not_silently_counted_as_zero(self):
        with self.assertRaisesRegex(ValueError, "Incomplete calendar"):
            parse_calendar("<html>Temporarily unavailable</html>", date(2026, 1, 2))

    def test_changed_tooltip_format_fails_closed(self):
        html = '<td id="a" data-date="2026-01-01"></td><tool-tip for="a">Activity unavailable</tool-tip>'
        with self.assertRaisesRegex(ValueError, "Unrecognized contribution"):
            parse_calendar(html, date(2026, 1, 1))

    def test_language_counts_exclude_forks_private_and_undetected(self):
        repos = [
            {"language": "Python", "fork": False},
            {"language": "Python", "fork": True},
            {"language": "Java", "private": True},
            {"language": None},
            {"language": "Rust", "fork": False},
        ]
        self.assertEqual(dict(language_groups(repos)), {"Python": 1, "Jupyter Notebook": 0, "Java": 0, "Dart": 0, "Other": 1})


if __name__ == "__main__":
    unittest.main()
