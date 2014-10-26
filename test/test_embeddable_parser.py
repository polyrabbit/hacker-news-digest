from unittest import TestCase
import requests

from page_content_extractor.embeddable import *

class EmbeddableParserTestCase(TestCase):

    def test_unknown_provider(self):
        self.assertRaises(ParseError, EmbeddableExtractor, 'whateve_provider', 'wharever_url')

    def test_youku_parser(self):
        parser = EmbeddableExtractor('YouKu', 'http://v.youku.com/v_show/id_XNzkxMTE3MTEy.html')
        self.assertEqual(parser.get_summary(),
                '<iframe width="560" height="315" src="http://player.youku.com/embed/XNzkxMTE3MTEy" frameborder="0" allowfullscreen></iframe>')

    def test_youtube_parser(self):
        parser = EmbeddableExtractor('Youtube', 'https://www.youtube.com/watch?v=db-7J5OaSag')
        self.assertEqual(parser.get_summary(),
                '<iframe width="560" height="315" src="//www.youtube.com/embed/db-7J5OaSag" frameborder="0" allowfullscreen></iframe>')

    def test_vimeo_parser(self):
        parser = EmbeddableExtractor('Vimeo', 'https://vimeo.com/105196878')
        self.assertEqual(parser.get_summary(),
                '<iframe width="560" height="315" src="//player.vimeo.com/video/105196878" frameborder="0" allowfullscreen></iframe>')

    def test_dailymotion_parser(self):
        parser = EmbeddableExtractor('dailYmotion', 'http://www.dailymotion.com/video/x26imxp_au-calme-english-subtitles_webcam')
        self.assertEqual(parser.get_summary(),
                '<iframe width="560" height="315" src="//www.dailymotion.com/embed/video/x26imxp" frameborder="0" allowfullscreen></iframe>')

    def test_tudou_parser(self):
        parser = EmbeddableExtractor('Tudou', 'http://www.tudou.com/albumplay/NBDgX_W2aJk/wjz6Oq52l7E.html')
        self.assertEqual(parser.get_summary(),
                '<iframe width="560" height="315" src="http://www.tudou.com/programs/view/html5embed.action?code=wjz6Oq52l7E" frameborder="0" allowfullscreen></iframe>')

    def test_ustream_parser(self):
        parser = EmbeddableExtractor('ustream', 'http://www.ustream.tv/recorded/9900109?utm_campaign=JPER&utm_medium=FlashPlayer&utm_source=embed')
        self.assertEqual(parser.get_summary(),
                '<iframe width="560" height="315" src="http://www.ustream.tv/embed/recorded/9900109?v=3&amp;wmode=direct" frameborder="0" allowfullscreen></iframe>')

    def test_bloomberg_parser(self):
        parser = EmbeddableExtractor('bloomberg', 'http://www.bloomberg.com/video/paul-graham-and-jessica-livingston-studio-1-0-10-09-J5e3sjvtRrys6nd286HWUA.html')
        self.assertEqual(parser.get_summary(),
                "<object data='http://www.bloomberg.com/video/embed/J5e3sjvtRrys6nd286HWUA?height=395&width=640' width=640 height=430 style='overflow:hidden;'></object>")

    def test_slideshare_parser(self):
        parser = EmbeddableExtractor('slideshare', 'http://www.slideshare.net/earnestagency/the-yes-factor')
        self.assertEqual(parser.get_summary(),
                         '<iframe src="http://www.slideshare.net/slideshow/embed_code/40684167" width="427" height="356" frameborder="0" marginwidth="0" marginheight="0" scrolling="no" style="border:1px solid #CCC; border-width:1px; margin-bottom:5px; max-width: 100%;" allowfullscreen> </iframe> <div style="margin-bottom:5px"> <strong> <a href="https://www.slideshare.net/earnestagency/the-yes-factor" title="The YES Factor: How to persuade business buyers to say yes." target="_blank">The YES Factor: How to persuade business buyers to say yes.</a> </strong> from <strong><a href="http://www.slideshare.net/earnestagency" target="_blank">Earnest</a></strong> </div>\n\n')

        self.assertRaises(requests.exceptions.HTTPError, EmbeddableExtractor, 'slideshare', 'http://www.slideshare.net/whatever404040404')
