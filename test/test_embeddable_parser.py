from unittest import TestCase

import requests

from page_content_extractor import parser_factory
from page_content_extractor.embeddable import *


class EmbeddableParserTestCase(TestCase):

    def test_unknown_provider(self):
        self.assertRaises(ParseError, EmbeddableExtractor, 'whateve_provider', 'wharever_url')

    def test_v_youku_com_parser(self):
        parser = EmbeddableExtractor('YouKu', 'http://v.youku.com/v_show/id_XNzkxMTE3MTEy.html')
        self.assertEqual(parser.get_content(),
                         '<iframe src="http://player.youku.com/embed/XNzkxMTE3MTEy" frameborder="0" allowfullscreen></iframe>')

    def test_youtube_com_parser(self):
        parser = parser_factory('https://www.youtube.com/watch?v=HlLCtjJzHVI')
        self.assertTrue(parser.get_content().startswith('<iframe'))

    def test_vimeo_com_parser(self):
        parser = EmbeddableExtractor('Vimeo', 'https://vimeo.com/105196878')
        self.assertEqual(parser.get_content(),
                         '<iframe src="//player.vimeo.com/video/105196878" frameborder="0" allowfullscreen loading="lazy"></iframe>')

    def test_dailymotion_com_parser(self):
        parser = EmbeddableExtractor('dailYmotion',
                                     'http://www.dailymotion.com/video/x26imxp_au-calme-english-subtitles_webcam')
        self.assertEqual(parser.get_content(),
                         '<iframe src="//www.dailymotion.com/embed/video/x26imxp" frameborder="0" allowfullscreen loading="lazy"></iframe>')

    def test_tudou_com_parser(self):
        parser = EmbeddableExtractor('Tudou',
                                     'http://www.tudou.com/albumplay/NBDgX_W2aJk/wjz6Oq52l7E.html')
        self.assertEqual(parser.get_content(),
                         '<iframe src="http://www.tudou.com/programs/view/html5embed.action?code=wjz6Oq52l7E" frameborder="0" allowfullscreen></iframe>')
        parser = EmbeddableExtractor('Tudou', 'http://www.tudou.com/programs/view/xlR2wzzJkSs/')
        self.assertEqual(parser.get_content(),
                         '<iframe src="http://www.tudou.com/programs/view/html5embed.action?code=xlR2wzzJkSs" frameborder="0" allowfullscreen></iframe>')

    def test_ustream_tv_parser(self):
        parser = EmbeddableExtractor('ustream',
                                     'http://www.ustream.tv/recorded/9900109?utm_campaign=JPER&utm_medium=FlashPlayer&utm_source=embed')
        self.assertEqual(parser.get_content(),
                         '<iframe src="http://www.ustream.tv/embed/recorded/9900109?v=3&amp;wmode=direct" frameborder="0" allowfullscreen loading="lazy"></iframe>')

    def test_bloomberg_com_parser(self):
        parser = EmbeddableExtractor('bloomberg',
                                     'http://www.bloomberg.com/video/paul-graham-and-jessica-livingston-studio-1-0-10-09-J5e3sjvtRrys6nd286HWUA.html')
        self.assertEqual(parser.get_content(),
                         "<object data='http://www.bloomberg.com/video/embed/J5e3sjvtRrys6nd286HWUA?height=395&width=640' width=640 height=430 style='overflow:hidden;'></object>")

    def test_slideshare_net_parser(self):
        parser = EmbeddableExtractor('slideshare',
                                     'http://www.slideshare.net/earnestagency/the-yes-factor')
        self.assertIn('<iframe', parser.get_content())

        self.assertRaises(requests.exceptions.HTTPError, EmbeddableExtractor, 'slideshare',
                          'http://www.slideshare.net/whatever404040404')

    def test_pdf_yt_parser(self):
        parser = EmbeddableExtractor('pdf', 'https://pdf.yt/d/KV90aIpCM7DqUpAv')
        self.assertEqual(parser.get_content(),
                         '<iframe src="https://pdf.yt/d/KV90aIpCM7DqUpAv/embed?sparse=0" allowfullscreen></iframe>')
        self.assertRaises(ParseError, EmbeddableExtractor, 'pdf', 'https://pdf.yt/gallery')

    def test_gist_github_com(self):
        parser = EmbeddableExtractor('<html></html>', 'https://gist.github.com/polyrabbit/5693787')
        self.assertEqual(parser.get_content(),
                         '<iframe src="https://gist.github.com/polyrabbit/5693787.pibb" style="width: 100%; height: 250px; border: 0;"></iframe>')
        self.assertRaises(ParseError, EmbeddableExtractor, 'whatever', 'https://gist.github.com/')
