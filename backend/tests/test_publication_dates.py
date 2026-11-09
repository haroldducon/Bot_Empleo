import unittest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.publication_dates import parse_publication_datetime, publication_window

BOGOTA = ZoneInfo("America/Bogota")
FIXED_NOW = datetime(2026, 10, 23, 16, 0, tzinfo=BOGOTA)


class PublicationDateTests(unittest.TestCase):
    def test_iso_timestamp_is_normalized_to_utc(self):
        parsed = parse_publication_datetime("2026-10-23T14:35:00-05:00")
        self.assertEqual(parsed, datetime(2026, 10, 23, 19, 35, tzinfo=timezone.utc))

    def test_spanish_relative_days(self):
        parsed = parse_publication_datetime("Publicado hace 2 días", now=FIXED_NOW)
        self.assertEqual(parsed, datetime(2026, 10, 21, 21, 0, tzinfo=timezone.utc))

    def test_yesterday_uses_bogota_calendar_day(self):
        parsed = parse_publication_datetime("Ayer", now=FIXED_NOW)
        self.assertEqual(parsed, datetime(2026, 10, 22, 5, 0, tzinfo=timezone.utc))

    def test_unknown_text_stays_unknown(self):
        self.assertIsNone(parse_publication_datetime("Fecha no informada", now=FIXED_NOW))

    def test_today_window_is_bogota_midnight_to_midnight(self):
        self.assertEqual(
            publication_window("today", now=FIXED_NOW),
            (
                datetime(2026, 10, 23, 5, 0, tzinfo=timezone.utc),
                datetime(2026, 10, 24, 5, 0, tzinfo=timezone.utc),
            ),
        )

    def test_yesterday_window_is_bogota_calendar_day(self):
        self.assertEqual(
            publication_window("yesterday", now=FIXED_NOW),
            (
                datetime(2026, 10, 22, 5, 0, tzinfo=timezone.utc),
                datetime(2026, 10, 23, 5, 0, tzinfo=timezone.utc),
            ),
        )

    def test_seven_day_window_includes_today_and_six_prior_dates(self):
        start, end = publication_window("7d", now=FIXED_NOW)
        self.assertEqual(start, datetime(2026, 10, 17, 5, 0, tzinfo=timezone.utc))
        self.assertEqual(end, datetime(2026, 10, 24, 5, 0, tzinfo=timezone.utc))

    def test_all_dates_has_no_window(self):
        self.assertIsNone(publication_window("all", now=FIXED_NOW))


if __name__ == "__main__":
    unittest.main()
