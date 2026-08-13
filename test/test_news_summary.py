# coding: utf-8
import os
import pathlib
import unittest
from unittest import TestCase, mock

import openai
import config
import db
from db.engine import session_scope
from db.summary import Model
from hacker_news.llm.openai import summarize_by_openai_family
from hacker_news.llm import qwen
from hacker_news.news import News


class NewsSummaryTestCase(TestCase):

    def test_small_text(self):
        news = News()
        content = 'Something went wrong, but don’t fret — let’s give it another shot.'  # from twitter
        summary, summarized_by = news.summarize(content)
        self.assertEqual(summary, content)
        self.assertEqual(summarized_by, Model.FULL)

    def test_iframe_text(self):
        news = News()
        content = f'<iframe src="//www.youtube.com/embed/{"a" * 1000}" frameborder="0" allowfullscreen loading="lazy"></iframe>'
        summary, summarized_by = news.summarize(content)
        self.assertEqual(summary, content)
        self.assertEqual(summarized_by, Model.EMBED)

    @unittest.skipUnless(not config.disable_local_qwen and config.local_qwen_path and
                         os.path.isfile(config.local_qwen_path),
                         'Local Qwen model is not installed or disabled')
    def test_summarize_by_local_qwen(self):
        news = News(score='11')
        fpath = os.path.join(os.path.dirname(__file__), 'fixtures/telnet.txt')
        with open(fpath, 'r') as fp:
            content = fp.read()
        summary = news.summarize_by_local_qwen(content)
        self.assertGreater(len(summary), 80)
        self.assertLess(len(summary), config.summary_size * 2)

    @unittest.skipUnless(openai.api_key, 'openai families are disabled')
    def test_summarize_by_openai_family(self):
        fpath = os.path.join(os.path.dirname(__file__), 'fixtures/telnet.txt')
        with open(fpath, 'r') as fp:
            content = fp.read()
        summary = summarize_by_openai_family(content)
        self.assertIn('elnet', summary, msg=f'actual summary: {summary!r}')
        self.assertFalse(summary.startswith(': '), msg=f'actual summary: {summary!r}')
        self.assertGreater(len(summary), 80, msg=f'actual summary: {summary!r}')
        self.assertLess(len(summary), config.summary_size * 2,
                        msg=f'actual summary: {summary!r}')

    def test_parse_step_answer(self):
        news = News('The guide to software development with Guix')
        self.assertEqual(news.parse_title_translation('"Guix软件开发指南"的中文翻译。'),
                         'Guix软件开发指南')
        self.assertEqual(news.parse_title_translation("《使用Guix进行软件开发的指南》的中文翻译。"),
                         '使用Guix进行软件开发的指南')
        self.assertEqual(news.parse_title_translation(
            '"The guide to software development with Guix"的中文翻译为:"使用Guix进行软件开发的指南"。'),
            '使用Guix进行软件开发的指南')

        self.assertEqual(
            news.parse_title_translation('Weird GPT-4 behavior for the specific string “ davidjl”'),
            'Weird GPT-4 behavior for the specific string “ davidjl”')
        self.assertEqual(news.parse_title_translation(
            '“Infinite Mac：在Web浏览器上发布经典的Macintosh系统和软件。”'),
            'Infinite Mac：在Web浏览器上发布经典的Macintosh系统和软件')
        self.assertEqual(
            news.parse_title_translation('“马克·扎克伯格谈论苹果的Vision Pro头戴式耳机”'),
            '马克·扎克伯格谈论苹果的Vision Pro头戴式耳机')
        self.assertEqual(news.parse_title_translation(
            '"Ask HN: Is it time to resurrect a Usenet clone? | Hacker News" 的中文翻译是“问 HN：是时候复活一个 Usenet 克隆了吗？| 黑客新闻”。'),
            '问 HN：是时候复活一个 Usenet 克隆了吗？| 黑客新闻')
        self.assertEqual(news.parse_title_translation(
            '我从OpenSnitch这个夏天学到了什么？(Note: This sentence is already in English and does not need to be translated.)'),
            '我从OpenSnitch这个夏天学到了什么？')

    # Avoid OpenAI summary overwritten by later shorter error message
    def test_fallback_when_new_fetch_failed(self):
        news = News(url='http://www.thehistoryblog.com/archives/67581')
        try:
            news.cache = db.summary.put(
                db.Summary(news.url, 'wonderful summary', Model.QWEN))
            content = 'The website is temporarily unable to service your request as it exceeded resource limit. Please try again later.'  # when site is overcrowded by HN users
            summary, summarized_by = news.summarize(content)
            self.assertEqual('wonderful summary', summary)
            self.assertEqual(news.cache.get_summary_model(), summarized_by)
        finally:
            with session_scope() as session:
                session.delete(news.cache)

    @mock.patch.object(News, 'parser')
    def test_all_from_cache(self, mock_news_parser):
        mock_news_parser.get_content.return_value = 'never called content, should read from cache'
        mock_news_parser.get_favicon_url.return_value = 'never called url, should read from cache'
        mock_news_parser.get_illustration.return_value = None
        news = News(title='Flea market find is medieval hand cannon',
                    url='non_exist_url')
        db_summary = db.Summary(news.url, 'wonderful summary', Model.OPENAI)
        try:
            db_summary.favicon = 'favicon.ico'
            db_summary.image_name = 'image_name.jpg'
            pathlib.Path(os.path.join(config.image_dir, db_summary.image_name)).touch()
            db.summary.put(db_summary)
            cached = news.pull_content()
            cached.birth = db_summary.birth
            cached.access = db_summary.access
            self.assertEqual(db_summary, cached)
            self.assertFalse(mock_news_parser.called)
        finally:
            with session_scope() as session:
                session.delete(news.cache)
                pathlib.Path(os.path.join(config.image_dir, db_summary.image_name)).unlink()
