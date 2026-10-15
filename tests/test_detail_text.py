import os
import tempfile
import unittest

from src.forexfactory.details import DetailCache, detail_text


class DetailText(unittest.TestCase):
    def test_keeps_the_pipe_format_the_frontend_parses(self):
        specs = [
            {"order": 2, "title": "Measures", "html": "Change in the price of goods;"},
            {"order": -10, "title": "Source", "html": '<a href="https://www.bls.gov/">Bureau of Labor Statistics</a> (latest release)'},
            {"order": 5, "title": "Why Traders<br>Care", "html": "Prices &amp; inflation\n matter"},
        ]
        self.assertEqual(
            detail_text(specs),
            "Source: Bureau of Labor Statistics (latest release) | Measures: Change in the price of goods; | Why Traders Care: Prices & inflation matter",
        )

    def test_empty(self):
        self.assertEqual(detail_text([]), "")


class Cache(unittest.TestCase):
    def test_refetches_near_events_after_a_day_and_keeps_far_ones(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "details.json")
            cache = DetailCache(path)
            cache.put(1, "Source: X", now=1000)
            cache.put(3, "", now=1000)
            cache.save()
            again = DetailCache(path)
            self.assertEqual(again.get(1), "Source: X")
            self.assertFalse(again.needs(1, near=True, now=1000 + 3600))
            self.assertTrue(again.needs(1, near=True, now=1000 + 25 * 3600))
            self.assertFalse(again.needs(1, near=False, now=1000 + 90 * 86400))
            self.assertTrue(again.needs(2, near=False, now=1000))
            self.assertTrue(again.needs(3, near=False, now=1000))


if __name__ == "__main__":
    unittest.main()
