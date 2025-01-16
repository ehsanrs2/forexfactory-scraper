# tests/test_details.py

import unittest
from src.forexfactory.detail_parser import detail_data_to_string

class TestDetailData(unittest.TestCase):

    def test_basic_dict(self):
        data = {
            "Description": "Line1\nLine2",
            "Speaker": "Name\r\nLastname"
        }
        result = detail_data_to_string(data)
        self.assertNotIn("\n", result)
        self.assertNotIn("\r", result)
        # انتظار داریم حتماً آنها با فاصله جایگزین شده باشند
        # شکل کلی مثلاً: "Description: Line1 Line2 | Speaker: Name Lastname"
        expected = "Description: Line1 Line2 | Speaker: Name Lastname"
        self.assertEqual(result, expected)

    def test_empty_dict(self):
        data = {}
        result = detail_data_to_string(data)
        self.assertEqual(result, "")


if __name__ == '__main__':
    unittest.main()
