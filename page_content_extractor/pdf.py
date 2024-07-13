# coding: utf-8
import logging
from io import BytesIO, StringIO
from urllib.parse import urljoin

from markupsafe import escape
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage

import config
from .utils import tokenize

logger = logging.getLogger(__name__)


class PdfExtractor(object):

    def __init__(self, raw_data, url=''):
        # TODO sort text according to their layouts
        self.article = ''
        self.url = url
        self.raw_data = raw_data

    def load(self, raw_data):
        pdf_fp = BytesIO(raw_data)
        output_fp = StringIO()
        laparams = LAParams()
        rsrcmgr = PDFResourceManager()
        device = TextConverter(rsrcmgr, output_fp, laparams=laparams)
        # Create a PDF interpreter object.
        interpreter = PDFPageInterpreter(rsrcmgr, device)

        # Process each page contained in the document.
        for page in PDFPage.get_pages(pdf_fp):
            interpreter.process_page(page)
            if len(output_fp.getvalue()) > config.max_content_size:
                logger.warning("%s too long, truncate to %d", self.url, len(output_fp.getvalue()))
                break

        self.article = output_fp.getvalue()

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
                partial_summaries.append(p)
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

        # Process each page contained in the document.
        for page in PDFPage.get_pages(pdf_fp):
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
        if p:
            yield ' '.join(p)

    def is_normal_paragraph(self, p):  # eligible to be a paragraph
        ascii_words = []
        for line in p.split('\n'):
            line = line.strip()
            if line.count('.') > 10:  # table of contents has many '...' or '. . .'
                return False
            tokens = line.split(' ')
            for tok in tokens:
                tok = tok.strip()
                if tok.isalnum() or tok in ('.', ','):
                    ascii_words.append(tok)
        return len(ascii_words) > 20

    def get_illustration(self):
        return None

    def get_favicon_url(self):
        return urljoin(self.url, '/favicon.ico')
