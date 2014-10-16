#coding: utf-8
import logging

from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from cStringIO import StringIO

from .exceptions import ParseError
from .utils import is_paragraph, word_count

logger = logging.getLogger(__name__)

class PdfExtractor(object):

    def __init__(self, raw_data):
        # TODO sort text according to their layouts
        try:
            self.load(raw_data)
        except Exception as e:
            raise ParseError(e)

    def load(self, raw_data):
        pdf_fp = StringIO(raw_data)
        output_fp = StringIO()
        codec = 'utf-8'
        laparams = LAParams()
        rsrcmgr = PDFResourceManager()
        device = TextConverter(rsrcmgr, output_fp, codec=codec, laparams=laparams)
        # Create a PDF interpreter object.
        interpreter = PDFPageInterpreter(rsrcmgr, device)

        # Process each page contained in the document.
        for page in PDFPage.get_pages(pdf_fp):
            interpreter.process_page(page)

        self.article = output_fp.getvalue()

    def get_summary(self, max_length=300):
        partial_summaries = []
        len_of_summary = 0
        for p in self.get_paragraphs():
            if is_paragraph(p):
                if len_of_summary + len(p) > max_length:
                    for word in p.split():
                        partial_summaries.append(word)
                        len_of_summary += len(word)
                        if len_of_summary > max_length:
                            partial_summaries.append('...')
                            return ' '.join(partial_summaries)
                else:
                    partial_summaries.append(p)
                    len_of_summary += len(p)
        return ' '.join(partial_summaries) or None

    def get_paragraphs(self):
        p = []
        has_began = False
        for line in self.article.split('\n'):
            if line.strip():
                has_began = True
                p.append(line.strip())
            elif has_began:  # end one paragraph
                yield ' '.join(p)
                has_began = False
                p = []
        if p:
            yield ' '.join(p)

    def get_top_image(self):
        return None

