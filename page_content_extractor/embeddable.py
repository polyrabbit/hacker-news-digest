# coding: utf-8
import logging
import re
from urllib.parse import urljoin
from urllib.parse import urlsplit

from bs4 import BeautifulSoup as BS

import config
from page_content_extractor.http import session
from .exceptions import ParseError

logger = logging.getLogger(__name__)


class EmbeddableExtractor(object):

    def __init__(self, html, url):
        host = urlsplit(url).hostname or ''
        provider = re.sub(r'^www\.', '', host.lower()).replace('.', '_')
        parser = getattr(self, '%s_parser' % provider,
                         self.default_parser)
        self.embed_html = parser(url)
        self.url = url
        self.doc = BS(html, features="lxml")

    def get_content(self, max_length=config.max_content_size):
        return self.embed_html

    @classmethod
    def is_embeddable(cls, url):
        host = urlsplit(url).hostname or ''
        provider = re.sub(r'^www\.', '', host.lower()).replace('.', '_')
        return hasattr(cls, '%s_parser' % provider)

    def get_illustration(self):
        return None

    def get_favicon_url(self):
        if not hasattr(self, '_favicon_url'):
            fa = self.doc.find('link', rel=re.compile('icon', re.I))
            favicon_path = fa.get('href', '/favicon.ico') if fa else '/favicon.ico'
            self._favicon_url = urljoin(self.url, favicon_path)
        return self._favicon_url

    def default_parser(self, url):
        raise ParseError('No idea how to parse %s' % url)

    def v_youku_com_parser(self, url):
        vid_mat = re.search(r'v\.youku\.com/v_show/id_(\w+?)\.html', url, re.I)
        if not vid_mat:
            raise ParseError('Invalid youku video url(%s)' % url)
        # TODO try bootstrap embed-responsive-item
        # see http://getbootstrap.com/components/#navbar-component-alignment
        return """<iframe src="http://player.youku.com/embed/%s" frameborder="0" """ \
               """allowfullscreen></iframe>""" % vid_mat.group(1)

    def youtube_com_parser(self, url):
        vid_mat = re.search(r'www\.youtube\.com/watch\?v=([^&]+)', url, re.I)
        if not vid_mat:
            raise ParseError('Invalid youtube video url(%s)' % url)
        return """<iframe src="//www.youtube.com/embed/%s" frameborder="0" """ \
               """allowfullscreen loading="lazy"></iframe>""" % vid_mat.group(1)

    def vimeo_com_parser(self, url):
        vid_mat = re.search(r'vimeo\.com/(\d+)', url, re.I)
        if not vid_mat:
            raise ParseError('Invalid vimeo video url(%s)' % url)
        return """<iframe src="//player.vimeo.com/video/%s" frameborder="0" """ \
               """allowfullscreen loading="lazy"></iframe>""" % vid_mat.group(1)

    def dailymotion_com_parser(self, url):
        vid_mat = re.search(r'www\.dailymotion\.com/video/([a-zA-Z0-9]+)_[-\w]+', url, re.I)
        if not vid_mat:
            raise ParseError('Invalid dailymotion video url(%s)' % url)
        return """<iframe src="//www.dailymotion.com/embed/video/%s" frameborder="0" """ \
               """allowfullscreen loading="lazy"></iframe>""" % vid_mat.group(1)

    def tudou_com_parser(self, url):
        vid_mat = re.search(r'www\.tudou\.com/albumplay/(\w+?)/(\w+?)\.html', url, re.I)
        if vid_mat:
            return """<iframe src="http://www.tudou.com/programs/view/html5embed.action?code=%s" frameborder="0" """ \
                   """allowfullscreen></iframe>""" % vid_mat.group(2)
        vid_mat = re.search(r'www\.tudou\.com/programs/view/([^/]+)/', url, re.I)
        if vid_mat:
            return """<iframe src="http://www.tudou.com/programs/view/html5embed.action?code=%s" frameborder="0" """ \
                   """allowfullscreen></iframe>""" % vid_mat.group(1)
        raise ParseError('Invalid tudou video url(%s)' % url)

    def ustream_tv_parser(self, url):
        vid_mat = re.search(r'www\.ustream\.tv/recorded/(\d+)', url, re.I)
        if not vid_mat:
            raise ParseError('Invalid ustream video url(%s)' % url)
        return """<iframe src="http://www.ustream.tv/embed/recorded/%s?v=3&amp;wmode=direct" frameborder="0" """ \
               """allowfullscreen loading="lazy"></iframe>""" % vid_mat.group(1)

    def bloomberg_com_parser(self, url):
        vid_mat = re.search(r'www\.bloomberg\.com/video/[-\w]+?-(\w+)\.', url, re.I)
        if not vid_mat:
            raise ParseError('Invalid bloomberg video url(%s)' % url)
        return """<object data='http://www.bloomberg.com/video/embed/%s?height=395&width=640' width=640 height=430 style='overflow:hidden;'></object>""" % vid_mat.group(
            1)

    def slideshare_net_parser(self, url):
        r = session.get('http://www.slideshare.net/api/oembed/2',
                        params={'url': url, 'format': 'json'})
        r.raise_for_status()
        return r.json()['html']

    def pdf_yt_parser(self, url):
        if not re.search(r'//pdf.yt/d/\w+', url, re.I):
            raise ParseError('Invalid pdf.yt embeddable url(%s)' % url)
        return '<iframe src="{}/embed?sparse=0" allowfullscreen></iframe>'.format(url)

    def gist_github_com_parser(self, url):
        path = urlsplit(url).path
        if path.count('/') < 2:
            raise ParseError('Invalid gist.github.com embeddable url(%s)' % url)
        # See https://milanaryal.com.np/how-to-embed-github-gists-in-an-iframe-tag/
        return f'<iframe src="https://gist.github.com{path}.pibb" style="width: 100%; height: 250px; border: 0;"></iframe>'
        # return '<script src="https://gist.github.com%s.js"></script>' % path
