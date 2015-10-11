#coding: utf-8
import os
from unittest import TestCase

from page_content_extractor.imgsz import *

class PdfParserTestCase(TestCase):

    def test_paragraph_parse_without_authors(self):
        fpath = os.path.join(os.path.dirname(__file__), 'fixtures/no-px-floating-point.svg')
        self.assertEqual(size(fpath), ('SVG', 90, 20))
