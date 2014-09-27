#coding: utf-8
import logging
import urllib2
from urlparse import urlsplit

from .exceptions import ParseError
from .html import HtmlContentExtractor
from .video import VideoExtractor, video_providers

logger = logging.getLogger(__name__)

# dispatcher
def legendary_parser_factory(url):
    # TODO what if url does not starts with 'http'?
    req = urllib2.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; '
        'Intel Mac OS X 10_10_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.94 Safari/537.36'})
    resp  = urllib2.urlopen(req)
    # .hostname is in lower case
    vp = urlsplit(resp.geturl()).hostname.split('.')[-2]
    if vp in video_providers:
        logger.info('Get a %s video to parse(%s)', vp, resp.geturl())
        try:
            return VideoExtractor(vp, resp.geturl())
        except ParseError:
            logger.info('%s is not a %s video, try another', resp.geturl(), vp)
    if resp.info().getmaintype() == 'text':
        logger.debug('Get an %s to parse', resp.info().gettype())
        return HtmlContentExtractor(resp)
    raise TypeError('I have no idea how the %s is formatted' % resp.info().gettype())

