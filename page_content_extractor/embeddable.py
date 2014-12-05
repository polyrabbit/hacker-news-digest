#coding: utf-8
import re
import logging

import requests

from .exceptions import ParseError

logger = logging.getLogger(__name__)

class EmbeddableExtractor(object):

    def __init__(self, video_provider, url):
        parser = getattr(self, '%s_parser' % video_provider.lower(),
                self.default_parser)
        self.embed_html = parser(url)

    def get_summary(self, max_length=300):
        return self.embed_html

    def get_top_image(self):
        return None

    def default_parser(self, url):
        raise ParseError('No idea how to parse %s' % url)
    
    def youku_parser(self, url):
        vid_mat = re.search(r'v\.youku\.com/v_show/id_(\w+?)\.html', url, re.I)
        if not vid_mat:
            raise ParseError('Invalid youku video url(%s)' % url)
        # TODO try bootstrap embed-responsive-item
        # see http://getbootstrap.com/components/#navbar-component-alignment
        return """<iframe src="http://player.youku.com/embed/%s" frameborder="0" """\
        """allowfullscreen></iframe>""" % vid_mat.group(1)

    def youtube_parser(self, url):
        vid_mat = re.search(r'www\.youtube\.com/watch\?v=([^&]+)', url, re.I)
        if not vid_mat:
            raise ParseError('Invalid youtube video url(%s)' % url)
        return """<iframe src="//www.youtube.com/embed/%s" frameborder="0" """\
        """allowfullscreen></iframe>""" % vid_mat.group(1)

    def vimeo_parser(self, url):
        vid_mat = re.search(r'vimeo\.com/(\d+)', url, re.I)
        if not vid_mat:
            raise ParseError('Invalid vimeo video url(%s)' % url)
        return """<iframe src="//player.vimeo.com/video/%s" frameborder="0" """\
        """allowfullscreen></iframe>""" % vid_mat.group(1)

    def dailymotion_parser(self, url):
        vid_mat = re.search(r'www\.dailymotion\.com/video/([a-zA-Z0-9]+)_[-\w]+', url, re.I)
        if not vid_mat:
            raise ParseError('Invalid dailymotion video url(%s)' % url)
        return """<iframe src="//www.dailymotion.com/embed/video/%s" frameborder="0" """\
        """allowfullscreen></iframe>""" % vid_mat.group(1)

    def tudou_parser(self, url):
        vid_mat = re.search(r'www\.tudou\.com/albumplay/(\w+?)/(\w+?)\.html', url, re.I)
        if vid_mat:
            return """<iframe src="http://www.tudou.com/programs/view/html5embed.action?code=%s" frameborder="0" """\
            """allowfullscreen></iframe>""" % vid_mat.group(2)
        vid_mat = re.search(r'www\.tudou\.com/programs/view/([^/]+)/', url, re.I)
        if vid_mat:
            return """<iframe src="http://www.tudou.com/programs/view/html5embed.action?code=%s" frameborder="0" """ \
                   """allowfullscreen></iframe>""" % vid_mat.group(1)
        raise ParseError('Invalid tudou video url(%s)' % url)

    def ustream_parser(self, url):
        vid_mat = re.search(r'www\.ustream\.tv/recorded/(\d+)', url, re.I)
        if not vid_mat:
            raise ParseError('Invalid ustream video url(%s)' % url)
        return """<iframe src="http://www.ustream.tv/embed/recorded/%s?v=3&amp;wmode=direct" frameborder="0" """\
        """allowfullscreen></iframe>""" % vid_mat.group(1)

    def bloomberg_parser(self, url):
        vid_mat = re.search(r'www\.bloomberg\.com/video/[-\w]+?-(\w+)\.', url, re.I)
        if not vid_mat:
            raise ParseError('Invalid bloomberg video url(%s)' % url)
        return """<object data='http://www.bloomberg.com/video/embed/%s?height=395&width=640' width=640 height=430 style='overflow:hidden;'></object>""" % vid_mat.group(1)

    def slideshare_parser(self, url):
        r = requests.get('http://www.slideshare.net/api/oembed/2', params={'url': url, 'format': 'json'})
        r.raise_for_status()
        return r.json()['html']

    def pdf_parser(self, url):
        if not re.search(r'//pdf.yt/d/\w+', url, re.I):
            raise ParseError('Invalid pdf.yt embeddable url(%s)' % url)
        return '<iframe src="{}/embed?sparse=0" allowfullscreen></iframe>'.format(url)

embeddables = frozenset(name.split('_')[0] for name in dir(EmbeddableExtractor) if name.endswith('_parser'))
