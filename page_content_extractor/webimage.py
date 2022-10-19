# coding: utf-8
import logging
from urllib.parse import urlparse, urljoin

import requests
from . import imgsz
from functools import lru_cache

logger = logging.getLogger(__name__)


class WebImage(object):
    MIN_PX = 100
    MIN_BYTES_SIZE = 4000
    MAX_BYTES_SIZE = 2.5 * 1024 * 1024
    SCALE_FROM_IMG_TO_TEXT = 22 * 22

    def __init__(self, src='', referrer='', **attrs):
        # e.g. http://www.washingtonpost.com/sf/investigative/2014/09/06/stop-and-seize/
        if not src:
            logger.info('No src')
            self._is_candidate = False
            return
        self.url = urljoin(referrer, src)
        self.referrer = referrer
        self.attrs = attrs

    @property
    def is_candidate(self):
        if hasattr(self, '_is_candidate'):
            return self._is_candidate
        self._is_candidate = False
        # see https://bitbucket.org/raphaelzhang/novel-reader/src/d5f1e60c5387bfbc375e89cada55b3b05370cb01/extractor.py#cl-717
        if self.url.startswith('data:image/'):
            logger.info('Image is encoded in base64, too short')
            return False
        attr_str = '%s %s %s %s' % (' '.join(self.attrs.get('class', [])),
                                    self.attrs.get('id', ''), self.attrs.get('alt', ''),
                                    urlparse(self.url).path.lower())
        if 'avatar' in attr_str or 'spinner' in attr_str:
            logger.info('Maybe this is an avatar/spinner(%s)', self.url)
            return False
        width, height = self.get_size()
        # self.img_area_px = self.equivalent_text_len()
        if not (width and height):
            logger.info('Failed on determining the image size of %s', self.url)
            return False
        if not self.check_dimension(width, height):
            logger.info('Failed on dimension check(width=%s height=%s) %s', width, height, self.url)
            return False
        if not self.check_image_bytesize():
            logger.info('Failed on image bytesize check, size is %s, %s', len(self.raw_data), self.url)
            return False
        self._is_candidate = True
        return True

    def get_size(self):
        height = self.attrs.get('height', '').strip().rstrip('px')
        width = self.attrs.get('width', '').strip().rstrip('px')

        if width.isdigit() and height.isdigit():
            return int(width), int(height)

        try:
            return imgsz.frombytes(self.raw_data)[1:]
        except ValueError as e:
            logger.error('Error while determing the size of %s, %s', self.url, e)
        return 0, 0

    @property
    def raw_data(self):
        if hasattr(self, '_raw_data'):
            return self._raw_data
        try:
            resp = requests.get(self.url, headers={'Referer': self.referrer})
            # meta info
            self.url = resp.url
            self._raw_data = resp.content
            self.content_type = resp.headers['Content-Type']
            return resp.content
        except (IOError, KeyError) as e:
            # if anything goes wrong, do not set self._raw_data
            # so it will try again the next time.
            logger.info('Failed to fetch img(%s), %s', self.url, e)
            return b''

    def to_text_len(self):
        return self.img_area_px / self.scale

    # See https://github.com/grangier/python-goose
    def check_dimension(self, width, height):
        """
        returns true if we think this is kind of a bannery dimension
        like 600 / 100 = 6 may be a fishy dimension for a good image
        """
        if width < self.MIN_PX or height < self.MIN_PX:
            return False
        dimension = 1.0 * width / height
        return .2 < dimension < 5

    def check_image_bytesize(self):
        return self.MIN_BYTES_SIZE < len(self.raw_data) < self.MAX_BYTES_SIZE

    def save(self, fp):
        if isinstance(fp, (str, bytes)):
            fp = open(fp, 'wb')
        fp.write(self.raw_data)
        fp.close()

    @classmethod
    @lru_cache(20)
    def from_attrs(cls, **kwargs):
        """
        A cached version of constructor, so as not need to repeatedly fetch from internet
        """
        return cls(**kwargs)

    @classmethod
    def from_node(cls, referrer, node):
        attrs = {'referrer': referrer}
        for key, value in list(node.attrs.items()):
            # convert SRC to src, and list to tuple because list is unhashable
            attrs[key.lower()] = tuple(value) if isinstance(value, list) else value
        return cls.from_attrs(**attrs)
