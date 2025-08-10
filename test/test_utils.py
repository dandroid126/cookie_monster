import unittest
from src import utils

class TestUtils(unittest.TestCase):
    def test_get_cookies(self):
        cookies = utils.get_cookies()
        self.assertTrue(len(cookies) > 0)
        for cookie in cookies:
            assert cookie.get("name")
            assert cookie.get("description")
            assert cookie.get("newAerialImage")
            assert not cookie.get("image")
