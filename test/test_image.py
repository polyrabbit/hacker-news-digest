# coding: utf-8
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

    def test_webp_failback_to_pil(self):
        fpath = os.path.join(os.path.dirname(__file__), 'fixtures/medium_Comment_f406ff2a89.png')
        self.assertEqual(size(fpath), ('WEBP', 1300, 787))


class WebImageTestCase(TestCase):

    @mock.patch('page_content_extractor.webimage.session')
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
        img = WebImage.from_attrs(a=1, b=2)
        self.assertFalse(img.is_candidate)
        self.assertFalse(mock_urljoin.called)

    @mock.patch('page_content_extractor.webimage.session')
    def test_guess_suffix_when_none(self, mock_requests):
        node = mock.Mock()
        node.attrs = {
            'src': 'https://camo.githubusercontent.com/75937896097d5a7022f8fafc71251e456a0e8d95b2a0b82e44c35a1b84368dc6/68747470733a2f2f61736369696e656d612e6f72672f612f3538393634302e737667',
        }
        mock_requests.get.return_value.url = node.attrs['src']
        mock_requests.get.return_value.headers = {'Content-Type': 'image/svg+xml;charset=utf-8'}
        img = WebImage.from_node('', node)
        self.assertEqual(img.uniq_name(), 'd41d8cd98f00b204e9800998ecf8427e.svg')

    def test_webp_compression(self):
        img = WebImage.from_json_str('{"url":"aaa"}')
        fpath = os.path.join(os.path.dirname(__file__), 'fixtures/home.png')
        with open(fpath, 'rb') as stream:
            img.raw_data = stream.read()
        self.assertEqual('.png', img.suffix)
        img.try_compress()
        self.assertEqual('.webp', img.suffix)
        self.assertEqual('c1a11593331f7678c7addb3c0001f57f.webp', img.uniq_name())

    def test_predominantly_white_color(self):
        for fname, is_white_color in (
                ('home.png', False),
                ('reddit.png', True),
                ('medium_Comment_f406ff2a89.png', False),
        ):
            fpath = os.path.join(os.path.dirname(__file__), 'fixtures', fname)
            img = WebImage.from_json_str('{"url":"%s"}' % fpath)
            with open(fpath, 'rb') as stream:
                img.raw_data = stream.read()
            self.assertEqual(is_white_color, img.is_predominantly_white_color())
