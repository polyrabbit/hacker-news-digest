# coding: utf-8
import os
from unittest import TestCase

from page_content_extractor.pdf import *


class PdfParserTestCase(TestCase):

    def test_paragraph_parse_without_authors(self):
        fpath = os.path.join(os.path.dirname(__file__), 'fixtures/cpi.pdf')
        with open(fpath, 'rb') as fp:
            parser = PdfExtractor(fp.read())
            self.assertIsNone(parser.get_illustration())
            content = parser.get_content()
            self.assertRegex(content, '^Systems code is often written in low-level languages')  # Should be no errors
            self.assertTrue(' We introduce code-pointer' in content)  # space between paragraphs

    def test_no_hang_for_large_pdf(self):
        fpath = os.path.join(os.path.dirname(__file__), 'fixtures/pldi24.pdf')
        with open(fpath, 'rb') as fp:
            parser = PdfExtractor(fp.read())
            self.assertIsNone(parser.get_illustration())
            content = parser.get_content()  # Should not hang
            self.assertRegex(content, '^We show that synthesizing recursive functional programs using ')  # No title or authors

    # def test_text_order(self):
    #     parser = PdfExtractor(open('/tmp/fm_21-76_us_army_survival_manual_2006.pdf', 'rb').read())
    #     self.assertIsNone(parser.get_illustration())
    #     print parser.get_content()
