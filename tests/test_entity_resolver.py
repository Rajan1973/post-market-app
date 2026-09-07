import unittest
from entity_resolution.resolver import EntityResolver

class TestEntityResolver(unittest.TestCase):

    def setUp(self):
        self.resolver = EntityResolver()

    def test_known_symbol_resolution(self):
        res1 = self.resolver.resolve_entity("TATA STEEL")
        self.assertTrue(res1["resolved"])
        self.assertEqual(res1["confidence"], 1.00)

        res2 = self.resolver.resolve_entity("Tata Steel")
        self.assertTrue(res2["resolved"])

    def test_unresolved_entity_queue(self):
        res = self.resolver.resolve_entity("UNKNOWN_FUTURE_CO_XYZ")
        self.assertFalse(res["resolved"])
        self.assertEqual(len(self.resolver.unresolved_queue), 1)
        self.assertEqual(self.resolver.unresolved_queue[0]["raw_name"], "UNKNOWN_FUTURE_CO_XYZ")

if __name__ == "__main__":
    unittest.main()
