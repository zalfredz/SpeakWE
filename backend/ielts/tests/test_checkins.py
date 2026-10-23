from datetime import date, datetime, timezone
from unittest import TestCase

from ielts.checkins import current_streak, local_date


def d(day):
    return date(2026, 10, day)


class CheckinRuleTests(TestCase):
    def test_local_date_crosses_midnight_jakarta(self):
        self.assertEqual(local_date(datetime(2026, 10, 22, 16, 59, tzinfo=timezone.utc), "Asia/Jakarta"), d(22))
        self.assertEqual(local_date(datetime(2026, 10, 22, 17, 1, tzinfo=timezone.utc), "Asia/Jakarta"), d(23))

    def test_streak_counts_consecutive_days(self):
        self.assertEqual(current_streak([d(20), d(21), d(22)], today=d(22)), 3)

    def test_streak_allows_today_missing(self):
        self.assertEqual(current_streak([d(20), d(21)], today=d(22)), 2)

    def test_streak_breaks_on_gap(self):
        self.assertEqual(current_streak([d(19), d(21), d(22)], today=d(22)), 2)
        self.assertEqual(current_streak([d(19), d(20)], today=d(22)), 0)

    def test_streak_ignores_duplicates_and_order(self):
        self.assertEqual(current_streak([d(22), d(20), d(21), d(22)], today=d(22)), 3)
