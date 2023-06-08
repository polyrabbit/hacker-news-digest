# coding: utf-8
import os
from unittest import TestCase

import config
from hacker_news.news import News, SummaryModel


class NewsSummaryTestCase(TestCase):

    def test_small_text(self):
        news = News()
        news.content = 'Something went wrong, but don’t fret — let’s give it another shot.'  # from twitter
        summary = news.summarize()
        self.assertEqual(summary, news.content)
        self.assertEqual(news.summarized_by, SummaryModel.FULL)

    def test_iframe_text(self):
        news = News()
        news.content = f'<iframe src="//www.youtube.com/embed/{"a" * 1000}" frameborder="0" allowfullscreen loading="lazy"></iframe>'
        summary = news.summarize()
        self.assertEqual(summary, news.content)
        self.assertEqual(news.summarized_by, SummaryModel.EMBED)

    def test_summarize_by_transformer(self):
        news = News(score='11')
        fpath = os.path.join(os.path.dirname(__file__), 'fixtures/telnet.txt')
        with open(fpath, 'r') as fp:
            news.content = fp.read()
        summary = news.summarize_by_transformer(news.content)
        self.assertGreater(len(summary), 80)
        self.assertLess(len(summary), config.summary_size * 2)
