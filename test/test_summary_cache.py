import unittest
from datetime import datetime, timedelta

import config
import db.summary
from db import translation, Translation, summary
from db.engine import session_scope


class TranslationCacheTestCase(unittest.TestCase):

    def test_translation_cache(self):
        translation.add('hello', 'hello', 'en')
        self.assertEqual('hello', translation.get('hello', 'en'))
        deleted = translation.expire()
        self.assertEqual(0, deleted)
        with session_scope() as session:
            trans = session.get(Translation, 'hello')
        trans.access = datetime.utcnow() - timedelta(seconds=translation.config.summary_ttl + 1)
        deleted = translation.expire()
        self.assertEqual(1, deleted)

    def test_summary_cache(self):
        summary.put(db.Summary('hello', 'world', db.summary.Model.OPENAI))
        self.assertEqual('world', summary.get('hello').summary)
        deleted = summary.expire()
        self.assertEqual(0, deleted)
        with session_scope() as session:
            summ = session.get(db.Summary, 'hello')
        summ.access = datetime.utcnow() - timedelta(seconds=summary.CONTENT_TTL + 1)  # not expired
        deleted = summary.expire()
        self.assertEqual(0, deleted)
        summ.access = datetime.utcnow() - timedelta(seconds=config.summary_ttl + 1)  # expired
        deleted = summary.expire()
        self.assertEqual(1, deleted)

    def test_exceeding_max_size(self):
        text = 'w' * summary.Summary.summary.type.length * 2
        summary.put(db.Summary('hello', text, db.summary.Model.OPENAI))
        self.assertEqual('w' * summary.Summary.summary.type.length, summary.get('hello').summary)
