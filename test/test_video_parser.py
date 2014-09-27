from unittest import TestCase

from page_content_extractor.video import *

class VideoParserTestCase(TestCase):

    def test_unknown_provider(self):
        self.assertRaises(ParseError, VideoExtractor, 'whateve_provider', 'wharever_url')

    def test_youku_parser(self):
        parser = VideoExtractor('YouKu', 'http://v.youku.com/v_show/id_XNzkxMTE3MTEy.html')
        self.assertEqual(parser.get_summary(),
                '<iframe width="560" height="315" src="http://player.youku.com/embed/XNzkxMTE3MTEy" frameborder="0" allowfullscreen></iframe>')

    def test_youtube_parser(self):
        parser = VideoExtractor('Youtube', 'https://www.youtube.com/watch?v=ocXb3qeg7Es')
        self.assertEqual(parser.get_summary(),
                '<iframe width="560" height="315" src="//www.youtube.com/embed/ocXb3qeg7Es" frameborder="0" allowfullscreen></iframe>')

    def test_vimeo_parser(self):
        parser = VideoExtractor('Vimeo', 'https://vimeo.com/105196878')
        self.assertEqual(parser.get_summary(),
                '<iframe width="560" height="315" src="//player.vimeo.com/video/105196878" frameborder="0" allowfullscreen></iframe>')

    def test_dailymotion_parser(self):
        parser = VideoExtractor('dailYmotion', 'http://www.dailymotion.com/video/x26imxp_au-calme-english-subtitles_webcam')
        self.assertEqual(parser.get_summary(),
                '<iframe width="560" height="315" src="//www.dailymotion.com/embed/video/x26imxp" frameborder="0" allowfullscreen></iframe>')

    def test_tudou_parser(self):
        parser = VideoExtractor('Tudou', 'http://www.tudou.com/albumplay/NBDgX_W2aJk/wjz6Oq52l7E.html')
        self.assertEqual(parser.get_summary(),
                '<iframe width="560" height="315" src="http://www.tudou.com/programs/view/html5embed.action?code=wjz6Oq52l7E" frameborder="0" allowfullscreen></iframe>')
