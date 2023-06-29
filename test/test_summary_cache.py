import unittest
from datetime import datetime, timedelta

import config
import db.summary
from db import translation, Translation, summary
from db.engine import session


class TranslationCacheTestCase(unittest.TestCase):

    def test_translation_cache(self):
        translation.add('hello', 'world', 'en')
        self.assertEqual('world', translation.get('hello', 'en'))
        deleted = translation.expire()
        self.assertEqual(0, deleted)
        trans = session.get(Translation, 'hello')
        trans.access = datetime.utcnow() - timedelta(seconds=translation.config.summary_ttl + 1)
        deleted = translation.expire()
        self.assertEqual(1, deleted)

    def test_summary_cache(self):
        summary.add('hello', 'world', db.summary.Model.OPENAI)
        self.assertEqual('world', summary.get('hello', db.summary.Model.OPENAI)[0])
        self.assertEqual('world', summary.get('hello')[0])  # ensure fallback works
        deleted = summary.expire()
        self.assertEqual(0, deleted)
        summ = session.get(db.Summary, 'hello')
        summ.access = datetime.utcnow() - timedelta(seconds=summary.CONTENT_TTL + 1)  # not expired
        deleted = summary.expire()
        self.assertEqual(0, deleted)
        summ.access = datetime.utcnow() - timedelta(seconds=config.summary_ttl + 1)  # expired
        deleted = summary.expire()
        self.assertEqual(1, deleted)

    def test_exceeding_max_size(self):
        text = 'w' * summary.Summary.summary.type.length * 2
        summary.add('hello', text, db.summary.Model.OPENAI)
        self.assertEqual('w' * summary.Summary.summary.type.length, summary.get('hello')[0])
