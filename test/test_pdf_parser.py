import os
from urllib2 import urlopen
from unittest import TestCase

from page_content_extractor.pdf import *

class PdfParserTestCase(TestCase):

    def test_simple_parse_with_no_errors(self):
        fpath = os.path.join(os.path.dirname(__file__), 'fixtures/cuckoo-undergrad.pdf')
        parser = PdfExtractor(open(fpath))
        self.assertIsNone(parser.get_top_image())
        parser.get_summary()  # no errors