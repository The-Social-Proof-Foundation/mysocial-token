import unittest
from scripts.supply_release_bot.bot import SupplyReleaseBot

class TestPriceCalculation(unittest.TestCase):
    def test_price_from_sqrtp(self):
        sqrtp = 2**96
        price = SupplyReleaseBot.price_from_sqrtp(sqrtp, 18, 18, True)
        self.assertAlmostEqual(price, 1.0, places=6)
