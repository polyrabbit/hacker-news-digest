#coding: utf-8
import logging
import urllib2

from .html import HtmlContentExtractor

logger = logging.getLogger(__name__)

# dispatcher
def legendary_parser_factory(url):
    req = urllib2.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; '
        'Intel Mac OS X 10_10_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.94 Safari/537.36'})
    resp  = urllib2.urlopen(req)
    if resp.info().getmaintype() == 'text':
        logger.debug('Get an %s to parse', resp.info().gettype())
        return HtmlContentExtractor(resp)
    raise TypeError('I have no idea how the %s is formatted' % resp.info().gettype())

