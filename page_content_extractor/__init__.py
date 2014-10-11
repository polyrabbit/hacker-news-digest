#coding: utf-8
import logging
import urllib2
from urlparse import urlsplit

from .exceptions import ParseError
from .html import HtmlContentExtractor
from .video import VideoExtractor, video_providers
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
    req = urllib2.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; '
        'Intel Mac OS X 10_10_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/38.0.2125.101 Safari/537.36'})
    # with urllib2.urlopen(req) as resp:
    resp = urllib2.urlopen(req)
    # .hostname is in lower case
    vp = urlsplit(resp.geturl()).hostname.split('.')[-2]
    if vp in video_providers:
        logger.info('Get a %s video to parse(%s)', vp, resp.geturl())
        try:
            return VideoExtractor(vp, resp.geturl())
        except ParseError:
            logger.info('%s is not a %s video, try another', resp.geturl(), vp)
    if resp.info().getmaintype() == 'text':
        logger.info('Get an %s to parse', resp.info().gettype())
        return HtmlContentExtractor(resp)
    if resp.info().gettype() == 'application/pdf':
        logger.info('Get a pdf to parse, %s', resp.geturl())
        try:
            return PdfExtractor(resp)
        except ParseError:
            logger.exception('Failed to parse this pdf file, %s', resp.geturl())
    raise TypeError('I have no idea how the %s is formatted' % resp.info().gettype())

