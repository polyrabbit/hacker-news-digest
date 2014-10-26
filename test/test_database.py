import random
from unittest import TestCase
from models import StartupNews, Image

class DataBaseTestCase(TestCase):

    def test_image_deleted(self):
        img_id = Image.add(content_type='image/jpeg', raw_data='010101')
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
        existing_keys = [n.url for n in StartupNews.query.all()]
        pk = StartupNews.add(**news)

        # Ensure saved
        self.assertEqual(StartupNews.query.get(pk).url, pk)
        self.assertEqual(Image.query.get(img_id).id, img_id)

        StartupNews.remove_except(existing_keys)
        # Ensure removed
        self.assertIsNone(StartupNews.query.get(pk))
        self.assertIsNone(Image.query.get(img_id))

    # def test_remove_on_empty_keys(self):
    #     # How to test a warning?
    #     self.storage.remove_except([])
