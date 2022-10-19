#coding: utf-8
import os
from unittest import TestCase
import mock

from page_content_extractor.imgsz import *
from page_content_extractor.webimage import WebImage

class SvgSizeTestCase(TestCase):

    def test_svg_with_no_px_and_floating_point_size(self):
        fpath = os.path.join(os.path.dirname(__file__), 'fixtures/no-px-floating-point.svg')
        self.assertEqual(size(fpath), ('SVG', 90, 20))

    def test_png_byte_compare(self):
        fpath = os.path.join(os.path.dirname(__file__), 'fixtures/home.png')
        self.assertEqual(size(fpath), ('PNG', 128, 128))

class WebImageTestCase(TestCase):

    @mock.patch('page_content_extractor.webimage.requests')
    def test_fetched_only_once(self, mock_requests):
        mock_requests.get.return_value.content = ''
        node = mock.Mock()
        node.attrs = {'src': 'https://avatars1.githubusercontent.com/u/2657334',
                     'whatever': 'whatever'}

        for _ in range(10):
            WebImage.from_node('https://github.com/polyrabbit/', node).is_candidate
        self.assertEqual(mock_requests.get.call_count, 1)

    @mock.patch('page_content_extractor.webimage.urljoin', autospec=True)
    def test_no_src(self, mock_urljoin):
        import logging
        logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - [%(asctime)s] %(message)s')
        img = WebImage.from_attrs(a=1, b=2)
        self.assertFalse(img.is_candidate)
        self.assertFalse(mock_urljoin.called)
