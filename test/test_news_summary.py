# coding: utf-8
import os
from unittest import TestCase

import config
from db.summary import Model
from hacker_news.news import News


class NewsSummaryTestCase(TestCase):

    def test_small_text(self):
        news = News()
        news.content = 'Something went wrong, but don’t fret — let’s give it another shot.'  # from twitter
        summary = news.summarize()
        self.assertEqual(summary, news.content)
        self.assertEqual(news.summarized_by, Model.FULL)

    def test_iframe_text(self):
        news = News()
        news.content = f'<iframe src="//www.youtube.com/embed/{"a" * 1000}" frameborder="0" allowfullscreen loading="lazy"></iframe>'
        summary = news.summarize()
        self.assertEqual(summary, news.content)
        self.assertEqual(news.summarized_by, Model.EMBED)

    def test_summarize_by_transformer(self):
        news = News(score='11')
        fpath = os.path.join(os.path.dirname(__file__), 'fixtures/telnet.txt')
        with open(fpath, 'r') as fp:
            news.content = fp.read()
        summary = news.summarize_by_transformer(news.content)
        self.assertGreater(len(summary), 80)
        self.assertLess(len(summary), config.summary_size * 2)

    def test_parse_step_answer(self):
        news = News('The guide to software development with Guix')
        self.assertEqual(news.parse_title_translation('"Guix软件开发指南"的中文翻译。'), 'Guix软件开发指南')
        self.assertEqual(news.parse_title_translation("《使用Guix进行软件开发的指南》的中文翻译。"), '使用Guix进行软件开发的指南')
        self.assertEqual(news.parse_title_translation('"The guide to software development with Guix"的中文翻译为:"使用Guix进行软件开发的指南"。'), '使用Guix进行软件开发的指南')

        self.assertEqual(news.parse_title_translation('Weird GPT-4 behavior for the specific string “ davidjl”'), 'Weird GPT-4 behavior for the specific string “ davidjl”')
        self.assertEqual(news.parse_title_translation('“Infinite Mac：在Web浏览器上发布经典的Macintosh系统和软件。”'), 'Infinite Mac：在Web浏览器上发布经典的Macintosh系统和软件')
        self.assertEqual(news.parse_title_translation('“马克·扎克伯格谈论苹果的Vision Pro头戴式耳机”'), '马克·扎克伯格谈论苹果的Vision Pro头戴式耳机')
        self.assertEqual(news.parse_title_translation('"Ask HN: Is it time to resurrect a Usenet clone? | Hacker News" 的中文翻译是“问 HN：是时候复活一个 Usenet 克隆了吗？| 黑客新闻”。'), '问 HN：是时候复活一个 Usenet 克隆了吗？| 黑客新闻')
        self.assertEqual(news.parse_title_translation('我从OpenSnitch这个夏天学到了什么？(Note: This sentence is already in English and does not need to be translated.)'), '我从OpenSnitch这个夏天学到了什么？')
