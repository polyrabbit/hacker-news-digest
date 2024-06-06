# coding: utf-8
import logging

import humanize

from page_content_extractor.http import session
from .embeddable import EmbeddableExtractor
from .exceptions import ParseError
from .html import HtmlContentExtractor
from .pdf import PdfExtractor

__all__ = ['ParseError', 'parser_factory']

logger = logging.getLogger(__name__)
jina_prefix = 'https://r.jina.ai/'


# dispatcher
def parser_factory(url, use_jina=False):
    """
        Returns the extracted object, which should have at least two
        methods `get_content` and `get_illustration`
    """
    if not url.startswith('http'):
        url = 'http://' + url
    headers = None
    if use_jina:
        headers = {'x-respond-with': 'html'}
    resp = session.get(url, headers=headers)
    # Some sites like science.org forbid us by responding 403, but still have meta description tags, so donot raise here
    if use_jina:  # Switch to origin url
        resp.raise_for_status()
        url = url.removeprefix(jina_prefix)
        resp.url = resp.url.removeprefix(jina_prefix)

    if EmbeddableExtractor.is_embeddable(url):
        logger.info('Get an embeddable to parse(%s)', resp.url)
        try:
            return EmbeddableExtractor(resp.text, resp.url)
        except Exception as e:
            logger.info('%s is not an embeddable, try another(%s)', resp.url, e)

    # if no content-type is provided, Chrome set as a html
    ct = resp.headers.get('content-type', 'text').lower()
    if ct.startswith('application/pdf'):  # Some pdfs even have charset indicator, eg. "application/pdf; charset=utf-8"
        logger.info(f'Get a pdf to parse, {resp.url}, size: {humanize.naturalsize(resp.headers.get("content-length", "-1"), binary=True)}')
        try:
            return PdfExtractor(resp.content, resp.url)
        except ParseError:
            logger.exception('Failed to parse this pdf file, %s', resp.url)
    elif ct.startswith('text') or 'html' in ct or 'xml' in ct or 'charset' in ct:
        logger.info('Get an %s to parse', ct)
        p = HtmlContentExtractor(resp.text, resp.url)
        if not use_jina and p.is_empty():
            logger.info('%s is empty? switch to jina', resp.url)
            try:
                return parser_factory(jina_prefix+url, use_jina=True)
            except Exception as e:
                logger.warning('jina %s throws an error: %s', jina_prefix+url, e)
        return p

    raise TypeError(f'I have no idea how the {ct} is formatted')
