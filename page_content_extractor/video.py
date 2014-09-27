#coding: utf-8
import re
import logging
from urlparse import urljoin

from .exceptions import ParseError

logger = logging.getLogger(__name__)

class VideoExtractor(object):

    def __init__(self, video_provider, url):
        parser = getattr(self, '%s_parser' % video_provider.lower(),
                self.default_parser)
        self.embed_html = parser(url)

    def get_summary(self):
        return self.embed_html

    def get_top_image(self):
        return None

    def default_parser(self, url):
        raise ParseError('No idea how to parse %s' % url)
    
    def youku_parser(self, url):
        vid_mat = re.search(r'v\.youku\.com/v_show/id_(\w+?)\.html', url, re.I)
        if not vid_mat:
            raise ParseError('Invalid youku video url')
        return """<iframe width="560" height="315" """\
        """src="http://player.youku.com/embed/%s" frameborder="0" """\
        """allowfullscreen></iframe>""" % vid_mat.group(1)

    def youtube_parser(self, url):
        vid_mat = re.search(r'www\.youtube\.com/watch\?v=(\w+)', url, re.I)
        if not vid_mat:
            raise ParseError('Invalid youtube video url')
        return """<iframe width="560" height="315" """\
        """src="//www.youtube.com/embed/%s" frameborder="0" """\
        """allowfullscreen></iframe>""" % vid_mat.group(1)

    def vimeo_parser(self, url):
        vid_mat = re.search(r'vimeo\.com/(\d+)', url, re.I)
        if not vid_mat:
            raise ParseError('Invalid vimeo video url')
        return """<iframe width="560" height="315" """\
        """src="//player.vimeo.com/video/%s" frameborder="0" """\
        """allowfullscreen></iframe>""" % vid_mat.group(1)

    def dailymotion_parser(self, url):
        vid_mat = re.search(r'www\.dailymotion\.com/video/([a-zA-Z0-9]+)_[-\w]+', url, re.I)
        if not vid_mat:
            raise ParseError('Invalid dailymotion video url')
        return """<iframe width="560" height="315" """\
        """src="//www.dailymotion.com/embed/video/%s" frameborder="0" """\
        """allowfullscreen></iframe>""" % vid_mat.group(1)

    def tudou_parser(self, url):
        vid_mat = re.search(r'www\.tudou\.com/albumplay/(\w+?)/(\w+?)\.html', url, re.I)
        if not vid_mat:
            raise ParseError('Invalid tudou video url')
        return """<iframe width="560" height="315" """\
        """src="http://www.tudou.com/programs/view/html5embed.action?code=%s" frameborder="0" """\
        """allowfullscreen></iframe>""" % vid_mat.group(2)

video_providers = frozenset(name.split('_')[0] for name in dir(VideoExtractor) if name.endswith('_parser'))