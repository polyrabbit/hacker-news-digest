# coding: utf-8
import io
import json
import logging
import math
import mimetypes
import pathlib
from functools import lru_cache
from hashlib import md5
from urllib.parse import urlparse, urljoin, unquote

from PIL import Image, ImageOps

from page_content_extractor.http import session
from . import imgsz

logger = logging.getLogger(__name__)


class WebImage(object):
    MIN_PX = 100
    MIN_BYTES_SIZE = 4000
    MAX_BYTES_SIZE = 10 * 1024 * 1024  # we have compression now
    MAX_WIDTH = 1200  # Wide enough for a sharp 600px preview on 2x screens
    SCALE_FROM_IMG_TO_TEXT = 22 * 22
    content_type = ''
    width = 0
    height = 0
    compressed = False

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
        url = urlparse(self.url.lower())  # the host tells too, e.g. avatars.githubusercontent.com
        attr_str = '%s %s %s %s%s' % (' '.join(self.attrs.get('class', [])),
                                      self.attrs.get('id', ''), self.attrs.get('alt', ''), url.netloc, url.path)
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
            logger.info('Failed on image bytesize check, size is %s, %s', len(self.raw_data),
                        self.url)
            return False
        if self.is_predominantly_white_color():
            return False
        self._is_candidate = True
        self.width, self.height = width, height
        return True

    def get_size(self):
        height_attr = self.attrs.get('height', '').strip().rstrip('px')
        width_attr = self.attrs.get('width', '').strip().rstrip('px')

        if width_attr.isdigit() and height_attr.isdigit():
            return int(width_attr), int(height_attr)

        try:
            w, h = imgsz.frombytes(self.raw_data)[1:]
            # Scale according to size attr
            if height_attr.isdigit():
                return w / (h / int(height_attr)), int(height_attr)
            if width_attr.isdigit():
                return int(width_attr), h / (w / int(width_attr))
            return w, h
        except Exception as e:
            logger.warning('Error while determine the size of %s, %s', self.url, e)
        return 0, 0

    @property
    def raw_data(self):
        if hasattr(self, '_raw_data'):
            return self._raw_data
        # Chrome's Accept negotiates avif, which Pillow can not decode
        with session.stream('GET', self.url, headers={'Referer': self.referrer, 'Accept': '*/*'}) as resp:
            # meta info
            self.url = resp.url
            resp.raise_for_status()
            bytes = []
            read_bytes = 0
            for content in resp.iter_content():
                if not content:
                    break
                bytes.append(content)
                read_bytes += len(content)
                if read_bytes > (17 << 20):
                    # To avoid infinite chunk response like - https://hookrace.net/time.gif
                    raise OverflowError(
                        f'too much or infinite content - already read {read_bytes} bytes')
        # if anything goes wrong, do not set self._raw_data so it will try again the next time.
        self._raw_data = b''.join(bytes)
        if 'Content-Type' in resp.headers:
            self.content_type = resp.headers['Content-Type']
        return self._raw_data

    @raw_data.setter
    def raw_data(self, value):
        self._raw_data = value

    def is_predominantly_white_color(self, predominance=.99, white_distance=10):
        try:
            maxpixels = 1024
            with Image.open(io.BytesIO(self.raw_data)) as img:
                img = img.convert('RGB')
                # img.show()
                if img.width and img.height:
                    maxpixels = img.width * img.height
                colors = img.getcolors(maxcolors=maxpixels)
                total_count = sum(count for count, color in colors)
                for count, color in colors:
                    if count / total_count > predominance and all(255 - white_distance <= value <= 255 for value in color):
                        logger.info('Maybe a solid color image(%s), dominant_pct=%f, RGB=%s', self.url, count / total_count, color)
                        return True
        except Exception as e:
            logger.warning('Failed on image colors check, %s, url=%s', e, self.url)
        return False

    # 'image/svg+xml;charset=utf-8' -> svg
    def guess_suffix(self):
        if not self.content_type:
            return ''
        return mimetypes.guess_extension(self.content_type.partition(';')[0].strip())

    def to_text_len(self):
        return self.img_area_px / self.scale

    def get_size_attrs(self, width):
        if self.width == 0:
            return ''
        return f'width="{width}" height="{math.ceil(self.height * (width / self.width))}"'

    # See https://github.com/grangier/python-goose
    def check_dimension(self, width, height):
        """
        returns true if we think this is kind of a bannery dimension
        like 600 / 100 = 6 may be a fishy dimension for a good image
        """
        if width < self.MIN_PX or height < self.MIN_PX:
            return False
        dimension = 1.0 * width / height
        # To ignore high images like https://reddit-image.s3.amazonaws.com/W3ichcYAUappVkzQXWLNbvriCZepRXi90OmGPD75tho.jpg
        return 0.67 < dimension < 3

    def check_image_bytesize(self):
        return self.MIN_BYTES_SIZE < len(self.raw_data) < self.MAX_BYTES_SIZE

    def try_compress(self):
        if self.compressed:  # Instances are cached, and encoding again would lose quality and change the file name
            return
        out = io.BytesIO()
        try:
            img = Image.open(io.BytesIO(self.raw_data))
            # Leave animations and high bit depth images (which RGB would clip) as they are.
            # The extra frames of MPO photos are only previews, so those are fine.
            if getattr(img, 'is_animated', False) and img.format != 'MPO' or img.mode.startswith(('I', 'F')):
                return
            # Convert before resizing, as palette images resize poorly.
            # Only RGB profiles still match the converted pixels.
            icc_profile = img.info.get('icc_profile') if img.mode in ('RGB', 'RGBA') else None
            img = ImageOps.exif_transpose(img).convert('RGBA' if img.has_transparency_data else 'RGB')
            img.thumbnail((self.MAX_WIDTH, img.height))
            img.save(out, format='webp', quality=50, icc_profile=icc_profile)
        except Exception as e:
            logger.info(f'Cannot compress {self.url}, {e}')  # e.g. SVG
            return
        if len(out.getbuffer()) >= len(self.raw_data):
            logger.info(f'got a bigger webp, src: {self.url}')
            return
        self.raw_data, self.suffix, self.compressed = out.getvalue(), '.webp', True
        self.width, self.height = img.size  # EXIF rotation may have swapped them

    def uniq_name(self):
        fname = md5(self.raw_data).hexdigest()
        return fname + self.suffix

    @property
    def suffix(self):
        if not hasattr(self, '_suffix'):
            suffix = pathlib.Path(urlparse(unquote(self.url)).path).suffix
            if not suffix:
                suffix = self.guess_suffix()
            if not suffix:
                try:
                    img = Image.open(io.BytesIO(self.raw_data))
                    if img.format:
                        suffix = '.' + img.format.lower()
                except:
                    pass
            self._suffix = suffix
        return self._suffix

    @suffix.setter
    def suffix(self, value):
        self._suffix = value

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
        if attrs.get('data-src'):  # lazy loaded images hold a placeholder in src
            attrs['src'] = attrs['data-src']
        return cls.from_attrs(**attrs)

    @classmethod
    def from_json_str(cls, json_str):
        if not json_str:
            return None
        attrs = json.loads(json_str)
        img = cls(src=attrs['url'])
        img.width, img.height = attrs.get('width', 0), attrs.get('height', 0)
        return img

    def to_json_str(self):
        attrs = {'url': self.url, 'width': self.width, 'height': self.height}
        return json.dumps(attrs, separators=(',', ':'))
