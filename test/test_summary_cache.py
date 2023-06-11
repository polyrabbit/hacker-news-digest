import tempfile
import time
import unittest

from hacker_news import translation, summary_cache
from hacker_news.dict_cache import ACCESS


class TranslationCacheTestCase(unittest.TestCase):

    def test_translation_cache(self):
        existing = translation.save(tempfile.gettempdir())
        translation.add('hello', 'world', 'en')
        self.assertEqual(translation.get('hello', 'en'), 'world')
        updated = translation.save(tempfile.gettempdir())
        self.assertEqual(existing + 1, updated)
        translation.cache['hello'][ACCESS] = int(time.time()) - translation.TTL - 1
        self.assertEqual(existing, translation.save(tempfile.gettempdir()))

    def test_summary_cache(self):
        existing = summary_cache.save(tempfile.gettempdir())
        summary_cache.add('hello', 'world', summary_cache.Model.OPENAI)
        self.assertEqual(summary_cache.get('hello', summary_cache.Model.OPENAI), 'world')
        updated = summary_cache.save(tempfile.gettempdir())
        self.assertEqual(existing + 1, updated)
        summary_cache.cache['hello'][ACCESS] = int(time.time()) - summary_cache.TTL - 1
        self.assertEqual(updated, summary_cache.save(tempfile.gettempdir()))
        summary_cache.cache['hello'][ACCESS] = int(time.time()) - summary_cache.EXPENSIVE_TTL - 1
        self.assertEqual(existing, summary_cache.save(tempfile.gettempdir()))
