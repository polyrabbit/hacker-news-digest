# coding: utf-8
import logging

from page_content_extractor.http import session
from .embeddable import EmbeddableExtractor
from .exceptions import ParseError
from .html import HtmlContentExtractor
from .pdf import PdfExtractor

__all__ = ['ParseError', 'parser_factory']

logger = logging.getLogger(__name__)


# dispatcher
def parser_factory(url):
    """
        Returns the extracted object, which should have at least two
        methods `get_content` and `get_illustration`
    """
    if not url.startswith('http'):
        url = 'http://' + url
    # Sad, urllib2 cannot handle cookie/gzip automatically
    resp = session.get(url)

    if EmbeddableExtractor.is_embeddable(url):
        logger.info('Get an embeddable to parse(%s)', resp.url)
        try:
            return EmbeddableExtractor(resp.text, resp.url)
        except Exception as e:
            logger.info('%s is not an embeddable, try another(%s)', resp.url, e)

    # if no content-type is provided, Chrome set as a html
    ct = resp.headers.get('content-type', 'text').lower()
    if ct.startswith('application/pdf'):  # Some pdfs even have charset indicator, eg. "application/pdf; charset=utf-8"
        logger.info(f'Get a pdf to parse, {resp.url}, size: {resp.headers.get("content-length", "-1")} bytes')
        try:
            return PdfExtractor(resp.content, resp.url)
        except ParseError:
            logger.exception('Failed to parse this pdf file, %s', resp.url)
    elif ct.startswith('text') or 'html' in ct or 'xml' in ct or 'charset' in ct:
        logger.info('Get an %s to parse', ct)
        return HtmlContentExtractor(resp.text, resp.url)

    raise TypeError(f'I have no idea how the {ct} is formatted')
