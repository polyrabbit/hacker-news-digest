#coding: utf-8
import os.path
import logging
import unittest
from unittest import TestCase

from bs4 import BeautifulSoup as BS
from page_content_extractor import *
from page_content_extractor.html import *

class PageContentExtractorTestCase(TestCase):

    maxDiff = None

    def test_purge(self):
        html_doc = """
        <html>good<script>whatever</script></html>
        """
        doc = BS(html_doc)
        HtmlContentExtractor.purge.im_func(object(), doc)
        self.assertIsNone(doc.find('script'))

    def test_text_len_with_comma(self):
        html_doc = u"""
        <html>good,，</html>
        """
        doc = BS(html_doc, from_encoding='utf-8')
        length = HtmlContentExtractor(html_doc).text_len(doc)
        self.assertEqual(length, 8)

    def test_parsing_empty_response(self):
        html_doc = u"""
        """
        self.assertEqual(HtmlContentExtractor(html_doc).article.text, '')

    def test_semantic_affect(self):
        assert HtmlContentExtractor.semantic_effect.im_func(object(),
                BS('<article>good</article>').article) == 2
        assert HtmlContentExtractor.semantic_effect.im_func(object(),
                BS('<p>good</p>').p) == 1
        assert HtmlContentExtractor.semantic_effect.im_func(object(),
                BS('<p class="conteNt">good</p>').p) == 2
        assert HtmlContentExtractor.semantic_effect.im_func(object(),
                BS('<p class="comment">good</p>').p) == .2

    # def test_calc_best_node(self):
    #     resp = urllib2.urlopen('http://graydon2.dreamwidth.org/193447.html')
    #     print HtmlContentExtractor(resp.read()).get_summary()

    # def test_check_image(self):
    #     html_doc = """
    #     <img src="http://www.washingtonpost.com/wp-srv/special/investigations/asset-forfeitures/map/images/map-fallback.jpg" />
    #     """
    #     img = WebImage('http://www.washingtonpost.com/sf/investigative/2014/09/06/stop-and-seize/', BS(html_doc).img)
    #     self.assertTrue(img.is_possible)

    def test_get_summary_from_all_short_paragraph(self):
        html_doc = u"""
        <p>1<h1>2</h1><div>3</div><h1>4</h1></p>
        """
        self.assertEqual(HtmlContentExtractor(html_doc).get_summary(), u'1 2 3 4')

    def test_get_summary_from_short_and_long_paragraph(self):
        html_doc = u"""
        <h3 class="post-name">HTTP/2: The Long-Awaited Sequel</h3>
        <span class="value">Thursday, October 9, 2014 2:01 AM</span>
        <h2>Ready to speed things up? </h2>
        <div>Ready to speed things up? </div>
        <p>Here at Microsoft, we’re rolling out support in Internet Explorer for the first significant rework of the Hypertext Transfer Protocol since 1999.  It’s been a while, so it’s due.</p>
        <p>While there have been lot of efforts to streamline Web architecture over the years, none have been on the scale of HTTP/2.  We’ve been working hard to help develop this new, efficient and compatible standard as part of the IETF HTTPbis Working Group. It’s called, for obvious reasons, HTTP/2 – and it’s available now, built into the new Internet Explorer starting with the <a href="http://preview.windows.com">Windows 10 Technical Preview</a>.  </p>
        """
        # print HtmlContentExtractor(html_doc).get_summary()
        self.assertEqual(HtmlContentExtractor(html_doc).get_summary(), u'Here at Microsoft, we’re rolling out support in Internet Explorer for the first significant rework of the Hypertext Transfer Protocol since 1999.  It’s been a while, so it’s due. '\
        u"While there have been lot of efforts to streamline Web architecture over the years, none have been on the scale of HTTP/2. ...")

    def test_get_summary_word_cut(self):
        html_doc = '<p>'+'1'*1000+'</p>'+'<p>'+'2'*1000+'</p>'
        summary = HtmlContentExtractor(html_doc).get_summary()
        self.assertNotIn('2', summary)
        self.assertTrue(summary.endswith('...'))

    def test_get_summary_with_preserved_tag(self):
        html_doc = '<pre>' + '1'*1000 + '</pre>'
        self.assertEqual(html_doc, HtmlContentExtractor(html_doc).get_summary())

    def test_get_summary_with_link_intensive(self):
        html_doc = '<div><p><a href="whatever">' + '1'*1000 + '</a></p>'+\
                   '<p>'+'2'*1000+'</p></div>'
        pp = HtmlContentExtractor(html_doc)
        pp.article = BS(html_doc).div
        self.assertTrue(pp.get_summary().startswith('2'*10))

    def test_get_summary_with_nested_div(self):
        html_doc = '<div><div>%s<div>%s</div></div></div>' % ('a'*1000, 'b'*1000)
        self.assertTrue(HtmlContentExtractor(html_doc).get_summary().startswith('b'))

    def test_get_summary_without_strip(self):
        html_doc = '<div>%s <span>%s</span></div>' % ('a'*200, 'b'*200)
        self.assertIn(' ', HtmlContentExtractor(html_doc).get_summary())

    def test_clean_up_html_not_modify_iter_while_looping(self):
        html_doc = open(os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            'fixtures/kim.com.html')).read().decode('utf-8')
        try:
            HtmlContentExtractor(html_doc)
        except AttributeError as e:
            self.fail('%s, maybe delete something while looping.' % e)

    def test_CJK(self):
        html_doc = u'我'*1000
        self.assertLess(len(HtmlContentExtractor(html_doc).get_summary()), 1000)

    def test_doctor(self):
        ar = legendary_parser_factory('http://www.bbc.com/news/magazine-29518319')
        print ar.get_summary()

if __name__ == '__main__':
    # basicConfig will only be called automatically when calling
    # logging.debug, logging.info ...
    # calling those method against a logger instance won't apply the basic config
    # see https://docs.python.org/2/library/logging.html#logging.basicConfig
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - [%(asctime)s] %(message)s')
    unittest.main()
