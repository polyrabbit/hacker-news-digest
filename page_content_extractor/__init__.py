# coding: utf-8
from . import utils

utils.monkey_patch_requests()

import logging

import requests

from .exceptions import ParseError
from .html import HtmlContentExtractor
from .embeddable import EmbeddableExtractor
from .pdf import PdfExtractor

__all__ = ['ParseError', 'legendary_parser_factory']

logger = logging.getLogger(__name__)


# dispatcher
def legendary_parser_factory(url):
    """
        Returns the extracted object, which should have at least two
        methods `get_summary` and `get_illustration`
    """
    if not url.startswith('http'):
        url = 'http://' + url
    # Sad, urllib2 cannot handle cookie/gzip automatically
    resp = requests.get(url)

    if EmbeddableExtractor.is_embeddable(url):
        logger.info('Get an embeddable to parse(%s)', resp.url)
        try:
            return EmbeddableExtractor(resp.text, resp.url)
        except Exception as e:
            logger.info('%s is not an embeddable, try another(%s)', resp.url, e)

    # if no content-type is provided, Chrome set as an html
    ct = resp.headers.get('content-type', 'text').lower()
    if ct.startswith('text') or 'html' in ct or 'xml' in ct or 'charset' in ct:
        logger.info('Get an %s to parse', ct)
        return HtmlContentExtractor(resp.text, resp.url)
    elif ct.startswith('application/pdf'):
        logger.info('Get a pdf to parse, %s', resp.url)
        try:
            return PdfExtractor(resp.content, resp.url)
        except ParseError:
            logger.exception('Failed to parse this pdf file, %s', resp.url)

    raise TypeError('I have no idea how the %s is formatted' % ct)
