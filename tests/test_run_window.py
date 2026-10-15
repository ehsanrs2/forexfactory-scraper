import unittest
from datetime import datetime, timezone

from run import month_chunks, next_month


def utc(*parts):
    return datetime(*parts, tzinfo=timezone.utc)


class MonthChunks(unittest.TestCase):
    def test_next_month_rolls_the_year(self):
        self.assertEqual(next_month(utc(2026, 12, 1)), utc(2027, 1, 1))

    def test_a_year_is_twelve_chunks(self):
        chunks = month_chunks(utc(2026, 1, 1), utc(2027, 1, 1))
        self.assertEqual(len(chunks), 12)
        self.assertEqual(chunks[1], (utc(2026, 2, 1), utc(2026, 3, 1)))

    def test_a_range_inside_a_month_stays_whole(self):
        self.assertEqual(
            month_chunks(utc(2026, 10, 13), utc(2026, 10, 16)),
            [(utc(2026, 10, 13), utc(2026, 10, 16))],
        )

    def test_a_range_across_months_splits_at_the_first(self):
        self.assertEqual(
            month_chunks(utc(2026, 10, 30), utc(2026, 11, 2)),
            [(utc(2026, 10, 30), utc(2026, 11, 1)), (utc(2026, 11, 1), utc(2026, 11, 2))],
        )


if __name__ == "__main__":
    unittest.main()
