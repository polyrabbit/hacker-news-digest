#coding: utf-8
import utils
utils.monkey_patch_requests()

import logging
from urlparse import urlsplit

import requests

from .exceptions import ParseError
from .html import HtmlContentExtractor
from .embeddable import EmbeddableExtractor, embeddables
from .pdf import PdfExtractor

logger = logging.getLogger(__name__)

# dispatcher
def legendary_parser_factory(url):
    """
        Returns the extracted object, which should have at least two
        methods `get_summary` and `get_top_image`
    """
    if not url.startswith('http'):
        url = 'http://' + url
    # Sad, urllib2 cannot handle cookie/gzip automatically
    resp = requests.get(url)

    # .hostname is in lower case
    provider = urlsplit(resp.url).hostname.split('.')[-2]
    if provider in embeddables:
        logger.info('Get a %s embeddable to parse(%s)', provider, resp.url)
        try:
            return EmbeddableExtractor(provider, resp.url)
        except Exception as e:
            logger.info('%s is not a %s embeddable, try another(%s)', resp.url, provider, e)

    ct = resp.headers.get('content-type', '').lower()
    if ct.startswith('text'):
        logger.info('Get an %s to parse', ct)
        return HtmlContentExtractor(resp.text, resp.url)
    elif ct.startswith('application/pdf'):
        logger.info('Get a pdf to parse, %s', resp.url)
        try:
            return PdfExtractor(resp.content)
        except ParseError:
            logger.exception('Failed to parse this pdf file, %s', resp.url)

    raise TypeError('I have no idea how the %s is formatted' % ct)

