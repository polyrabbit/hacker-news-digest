import unittest
from datetime import datetime, timedelta

from hackernews import HackerNews


class TestHackerNewsParser(unittest.TestCase):

    def setUp(self):
        self.hn = HackerNews()

    def test_parsed_score(self):
        """Every score should be a digit"""
        news_list = self.hn.parse_news_list()
        self.assertGreater(len(news_list), 0)

        has_score = False
        has_submit_time = False
        for news in news_list:
            self.assertGreater(len(news['title']), 0)
            self.assertGreater(len(news['url']), 0)
            if news['score'] is not None and news['score'].isdigit():
                has_score = True
            if news['submit_time'] is not None and isinstance(news['submit_time'], datetime):
                has_submit_time = True
        self.assertEqual(has_score, True)
        self.assertEqual(has_submit_time, True)

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

    def test_parse_datetime(self):
        self.assertAlmostEqual(self.hn.human2datetime('2 minutes ago').timestamp(),
                               (datetime.utcnow() - timedelta(minutes=2)).timestamp(), delta=1)
