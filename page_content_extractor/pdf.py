# coding: utf-8
import re
from io import BytesIO, StringIO
from urllib.parse import urljoin

from markupsafe import escape
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage

import config
from .utils import tokenize


class PdfExtractor(object):

    def __init__(self, raw_data, url=''):
        # TODO sort text according to their layouts
        self.url = url
        self.raw_data = raw_data

    def get_content(self, max_length=config.max_content_size):
        partial_summaries = []
        len_of_summary = 0
        for p in self.get_paragraphs():
            if not self.is_normal_paragraph(p):
                continue
            if len_of_summary + len(p) >= max_length:
                for word in tokenize(p):
                    partial_summaries.append(escape(word))
                    len_of_summary += len(word)
                    if len_of_summary > max_length:
                        return ' '.join(partial_summaries)
            else:
                partial_summaries.append(escape(p))
                len_of_summary += len(p)
        return ' '.join(partial_summaries)

    def get_paragraphs(self):
        p = []
        has_began = False

        pdf_fp = BytesIO(self.raw_data)
        output_fp = StringIO()
        laparams = LAParams()
        rsrcmgr = PDFResourceManager()
        device = TextConverter(rsrcmgr, output_fp, laparams=laparams)
        # Create a PDF interpreter object.
        interpreter = PDFPageInterpreter(rsrcmgr, device)

        # Cap pages, as rejected paragraphs, e.g. a long table of contents, cost no content budget
        for page in PDFPage.get_pages(pdf_fp, maxpages=30):
            interpreter.process_page(page)
            for line in output_fp.getvalue().split('\n'):
                line = line.strip()
                if line and line.isprintable() and line.lower() != 'abstract':  # avoid handling \x01\x02...
                    has_began = True
                    p.append(line.strip())
                elif has_began:  # end one paragraph
                    yield '\n'.join(p)
                    has_began = False
                    p = []
            output_fp.seek(0)
            output_fp.truncate()  # or a shorter page leaves the tail of the last one
        if p:
            yield ' '.join(p)

    def is_normal_paragraph(self, p):  # eligible to be a paragraph
        # A table of contents is either split into short blocks of titles and page numbers,
        # or kept as one with many '...' or '. . .'
        if any(line.count('.') > 10 for line in p.split('\n')):
            return False
        # Count words with punctuation too, e.g. "end.", but not numbers
        return len(re.findall(r'[^\W\d_]+', p)) > 20

    def get_illustration(self):
        return None

    def get_favicon_url(self):
        return urljoin(self.url, '/favicon.ico')
