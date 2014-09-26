import random
from unittest import TestCase
from db import *

class NewsParserTestCase(TestCase):

    def setUp(self):
        self.storage = SnStorage()

    def test_image_deleted(self):
        img_id = ImageStorage().put(raw_data='010101',
                      content_type='image/jpeg')
        news = dict(
                rank = 1,
                title = 'title',
                url = 'http://localhost/%s' % random.random(),
                comhead = 'localhost',
                score = '100',
                author = 'poly',
                author_link = 'http://localhost/',
                submit_time = '10 hours ago',
                comment_cnt = '100',
                comment_url = 'http://localhost',
                summary = 'Hello world!',
                img_id = img_id
        )
        existing_keys = [n.url for n in self.storage.get_all()]
        pk = self.storage.put(**news)

        im_storage = ImageStorage()
        # Ensure saved
        self.assertEqual(self.storage.get(pk).url, pk)
        self.assertEqual(im_storage.get(img_id).id, img_id)

        self.storage.remove_except(existing_keys)
        # Ensure removed
        self.assertIsNone(self.storage.get(pk))
        self.assertIsNone(im_storage.get(img_id))

    def test_remove_on_empty_keys(self):
        # How to test a warning?
        self.storage.remove_except([])