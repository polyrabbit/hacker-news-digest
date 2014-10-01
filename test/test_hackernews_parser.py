import unittest

from hackernews import HackerNews

class TestHackerNewsParser(unittest.TestCase):

    def setUp(self):
        self.hn = HackerNews()

    def test_parsed_score(self):
        """Every score should be a digit"""
        for news in self.hn.parse_news_list():
            self.assertTrue(news['score'] is None or \
                    news['score'].isdigit())

    def test_parse_comhead(self):
        # test removed www
        self.assertEqual(self.hn.parse_comhead('www.googlE.com'),
                         'google.com')
        # test whole hostname
        self.assertEqual(self.hn.parse_comhead('plus.googlE.com'),
                         'plus.google.com')
        # test hostname with github user
        self.assertEqual(self.hn.parse_comhead('www.github.com/polyrabbit'),
                         'github.com/polyrabbit')
        self.assertEqual(self.hn.parse_comhead('github.com/'),
                         'github.com')