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
        e = HtmlContentExtractor(html_doc)
        e.purge()
        self.assertIsNone(e.doc.find('script'))

    def test_text_len_with_comma(self):
        html_doc = u"""
        <html>good,，</html>
        """
        doc = BS(html_doc, from_encoding='utf-8')
        length = HtmlContentExtractor(html_doc).calc_effective_text_len(doc)
        self.assertEqual(length, 8)

    def test_parsing_empty_response(self):
        html_doc = u"""
        """
        self.assertEqual(HtmlContentExtractor(html_doc).article.text, '')

    def test_no_content(self):
        html_doc = u"""
        <!DOCTYPE html>
        <html class="no-js" dir="ltr" lang="en" prefix="content: http://purl.org/rss/1.0/modules/content/ dc: http://purl.org/dc/terms/ foaf: http://xmlns.com/foaf/0.1/ og: http://ogp.me/ns# rdfs: http://www.w3.org/2000/01/rdf-schema# sioc: http://rdfs.org/sioc/ns# sioct: http://rdfs.org/sioc/types# skos: http://www.w3.org/2004/02/skos/core# xsd: http://www.w3.org/2001/XMLSchema#">
            <body class="html not-front not-logged-in page-node page-node- page-node-371988 node-type-ubernode section-feature">
            <div class="l-page ember-init-hide">
            <header class="l-header container-fluid" role="banner"></header>
            <div class="l-main">
            <div class="l-content container-fluid" id="main" role="main">
            <article about="/feature/remembering-george-mueller-leader-of-early-human-spaceflight" class="node node--ubernode node--full node--ubernode--full" role="article" typeof="sioc:Item foaf:Document">
            <header>
            <span class="rdf-meta element-hidden" content="Remembering George Mueller, Leader of Early Human Spaceflight" property="dc:title"></span> </header>
            <div class="node__content">
            </div>
            </article>
            </div>
            </div>
            <footer class="l-footer container-fluid" role="contentinfo"></footer>
            </div>


            </body>
        </html>
        """
        page = HtmlContentExtractor(html_doc)
        self.assertEquals(page.calc_effective_text_len(page.article), 0)
        self.assertEquals(page.get_summary(), u'')

    def test_semantic_affect(self):
        # They are static methods
        self.assertTrue(HtmlContentExtractor.has_positive_effect(BS('<article>good</article>').article))
        self.assertFalse(HtmlContentExtractor.has_negative_effect(BS('<p>good</p>').p))
        self.assertFalse(HtmlContentExtractor.has_positive_effect(BS('<p>good</p>').p))
        self.assertTrue(HtmlContentExtractor.has_positive_effect(BS('<p class="conteNt">good</p>').p))
        self.assertTrue(HtmlContentExtractor.has_negative_effect(BS('<p class="comment">good</p>').p))

    # def test_calc_best_node(self):
    #     resp = urllib2.urlopen('http://graydon2.dreamwidth.org/193447.html')
    #     print HtmlContentExtractor(resp.read()).get_summary()

    def test_check_image(self):
        html_doc = """
        <img src="http://www.washingtonpost.com/wp-srv/special/investigations/asset-forfeitures/map/images/map-fallback.jpg" />
        """
        img = WebImage.from_attrs(
            src='http://www.washingtonpost.com/wp-srv/special/investigations/asset-forfeitures/map/images/map-fallback.jpg',
            referrer='http://www.washingtonpost.com/')
        self.assertTrue(img.is_candidate)

    def test_non_top_image(self):
        self.assertIsNone(HtmlContentExtractor('').get_illustration())

    def test_image_from_meta(self):
        html_doc = """
        <meta property="og:image" content="http://ww1.sinaimg.cn/large/e724cbefgw1exdnntkml4j2079044jrd.jpg">
        <meta property="og:image" content="http://ww3.sinaimg.cn/large/e724cbefgw1exdqgziee9j207306mq2z.jpg">
        <body>
        <img src="https://assets-cdn.github.com/images/spinners/octocat-spinner-128.gif" alt="Octocat Spinner Icon" class="m-2" width="28">
        </body>
        """
        # should choose the first meta image
        self.assertEquals(HtmlContentExtractor(html_doc).get_illustration().url,
                          'http://ww1.sinaimg.cn/large/e724cbefgw1exdnntkml4j2079044jrd.jpg')

    @unittest.skip('Skipped because summary is too short')
    def test_get_summary_from_all_short_paragraph(self):
        html_doc = u"""
        <p>1<h1>2</h1><div>3</div><h1>4</h1></p>
        """
        self.assertEqual(HtmlContentExtractor(html_doc).get_summary(), u'1 2 3 4')

    def test_get_summary_from_short_and_long_paragraph(self):
        html_doc = u"""
        <h3 class="post-name">HTTP/2: The Long-Awaited Sequel</h3>
        <span class="post-date">Thursday, October 9, 2014 2:01 AM</span>
        <h2>Ready to speed things up? </h2>
        <p>Here at Microsoft, we’re rolling out support in Internet Explorer for the first significant rework of the Hypertext Transfer Protocol since 1999.  It’s been a while, so it’s due.</p>
        <p>While there have been lot of efforts to streamline Web architecture over the years, none have been on the scale of HTTP/2.  We’ve been working hard to help develop this new, efficient and compatible standard as part of the IETF HTTPbis Working Group. It’s called, for obvious reasons, HTTP/2 – and it’s available now, built into the new Internet Explorer starting with the <a href="http://preview.windows.com">Windows 10 Technical Preview</a>.</p>
        """
        self.assertEqual(HtmlContentExtractor(html_doc).get_summary(), u'Here at Microsoft, we’re rolling out support in Internet Explorer for the first significant rework of the Hypertext Transfer Protocol since 1999.  It’s been a while, so it’s due. '\
        u"While there have been lot of efforts to streamline Web architecture over the years, none have been on the scale of HTTP/2. ...")

    def test_get_summary_word_cut(self):
        html_doc = '<p>'+'1 '*500+'</p>'+'<p>'+'2 '*500+'</p>'
        summary = HtmlContentExtractor(html_doc).get_summary()
        self.assertNotIn('2', summary)
        self.assertTrue(summary.endswith('...'))

    @unittest.skip('No preserved tag check for now')
    def test_get_summary_with_preserved_tag(self):
        html_doc = '<pre>' + '11 '*400 + '</pre>'
        self.assertEqual(html_doc, HtmlContentExtractor(html_doc).get_summary(10))
        html_doc = '<pre><code>' + '11\n'*400 + '</code>'+'what you think?'*200+'</pre>'
        # print HtmlContentExtractor(html_doc).get_summary(10)
        self.assertEqual(HtmlContentExtractor(html_doc).get_summary(10), '<pre><code>%s</code></pre>' % '\n'.join(['11']*5))

    @unittest.skip('No need for now')
    def test_get_summary_with_link_intensive(self):
        html_doc = '<div><p><a href="whatever">' + '1 '*500 + '</a></p>'+\
                   '<p>'+'2 '*500+'</p></div>'
        pp = HtmlContentExtractor(html_doc)
        pp.article = BS(html_doc).div
        self.assertTrue(pp.get_summary().startswith('2 '*10))

    def test_escaped_summary(self):
        html_doc = '<code>&lt;a href=&quot;&quot; title=&quot;&quot;&gt; &lt;</code>'
        article = HtmlContentExtractor(html_doc)
        # TODO test longer html
        self.assertEqual(article.get_summary(), '&lt;a href=&#34;&#34; title=&#34;&#34;&gt; &lt;')

    def test_no_extra_spaces_between_tags(self):
        html_doc = '<p><strong><span style="color:red">R</span></strong>ed</p>'
        article = HtmlContentExtractor(html_doc)
        self.assertEqual(article.get_summary(), 'Red')

    def test_get_summary_with_meta_class(self):
        html_doc = '<div><p class="meta">good</p><p>bad</p></div>'
        article = HtmlContentExtractor(html_doc)
        self.assertEqual(article.get_summary(4), 'bad')

    def test_get_summary_with_nested_div(self):
        html_doc = '<div><div>%s<div>%s</div></div></div>' % ('a '*500, 'b '*500)
        self.assertTrue(HtmlContentExtractor(html_doc).get_summary().startswith('a'))

    def test_empty_title(self):
        """Empty title shouldn't be None"""
        html_doc = '<title></title>'
        article = HtmlContentExtractor(html_doc)
        self.assertEqual(article.title, '')

    def test_cut_content_to_length(self):
        # Test not breaking a sentence in the middle
        html_doc = '<pre>good</pre>'
        self.assertEqual(HtmlContentExtractor.cut_content_to_length(BS(html_doc).pre, 1), (html_doc, 4))

    def test_cut_content_to_length_break_on_lines(self):
        html_doc = '<pre>good\ngood</pre>'
        self.assertEqual(HtmlContentExtractor.cut_content_to_length(BS(html_doc).pre, 1), ('<pre>good</pre>', 4))
        html_doc = '<pre><code>good\ngood</code></pre>'
        self.assertEqual(HtmlContentExtractor.cut_content_to_length(BS(html_doc).pre, 1), ('<pre><code>good</code></pre>', 4))

    def test_cut_content_to_length_with_self_closing_tag(self):
        html_doc = '<pre>good<br>and<img></pre>'
        self.assertEqual(HtmlContentExtractor.cut_content_to_length(BS(html_doc).pre, 10), ('<pre>good<br/>and<img/></pre>', 7))

    def test_get_summary_without_strip(self):
        html_doc = '<div>%s <span>%s</span></div>' % ('a'*200, 'b'*200)
        self.assertIn(' ', HtmlContentExtractor(html_doc).get_summary())

    def test_favicon_url(self):
        html_doc = '''
        <html>
            <head>
                <link rel="shortcut icon" href="/ico.favicon">
            </head>
            <body>
                good
            </body>
        </html>
        '''
        self.assertEqual('http://local.host/ico.favicon', HtmlContentExtractor(html_doc, 'http://local.host').get_favicon_url())

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

    def test_tags_separated_by_space(self):
        html_doc = u"""
        <article><p>Python has a GIL, right? Not quite - PyPy STM is a python implementation
without a GIL, so it can scale CPU-bound work to several cores.
PyPy STM is developed by Armin Rigo and Remi Meier,
and supported by community <em>donations</em>.</p></article>
        """
        print HtmlContentExtractor(html_doc).get_summary(1000)
        self.assertTrue(HtmlContentExtractor(html_doc).get_summary(1000).endswith('by community donations.'))

    def test_article_with_info_attr(self):
        ar = legendary_parser_factory('http://www.infoq.com/cn/news/2014/11/fastsocket-github-opensource')
        self.assertTrue(unicode(ar.article).startswith('<div id="content">'))
        self.assertTrue(unicode(ar.get_summary()).startswith(u'2014年10月18日'))
        self.assertTrue(unicode(ar.get_summary()).endswith(u'...'))

    def test_article_title_donot_match_doc_title(self):
        ar = legendary_parser_factory('http://www.technologyreview.com/news/532826/material-cools-buildings-by-sending-heat-into-space/')
        summary = unicode(ar.get_summary())
        print summary
        self.assertTrue(summary.startswith(u'A material that simultaneously'))
        self.assertTrue(summary.endswith(u'...'))

    def test_content_with_meta_in_attr(self):
        ar = legendary_parser_factory('http://www.nature.com/nature/journal/v516/n7529/full/nature14005.html')
        summary = unicode(ar.get_summary())
        self.assertTrue(summary.startswith(u'The capture of transient scenes'))
        self.assertTrue(summary.endswith(u'...'))

    def test_common_sites_forbes(self):
        ar = legendary_parser_factory('http://www.forbes.com/sites/groupthink/2014/10/21/we-just-thought-this-is-how-you-start-a-company-in-america/')
        self.assertTrue(unicode(ar.article).startswith('<div class="article_content col-md-10 col-sm-12">'))
        self.assertTrue(unicode(ar.get_summary()).startswith('Kind of like every baseball player will try'))

    def test_common_sites_ruanyifeng(self):
        ar = legendary_parser_factory('http://www.ruanyifeng.com/blog/2014/10/real-leadership-lessons-of-steve-jobs.html')
        self.assertTrue(unicode(ar.article).startswith('<article class="hentry">'))
        self.assertTrue(unicode(ar.get_summary()).startswith(u'2011年11月出版的'))
        self.assertTrue(unicode(ar.get_summary()).endswith(u'...'))

    # @unittest.skip('local test only')
    def test_shit(self):
        html_doc = u"""
        <li id="ref1">
            <span class="vcard author">
                <span class="fn">Fuller, P. W. W.</span>
            </span>
            <span class="title">An introduction to high speed photography and photonics</span>.
            <span class="source-title">Imaging Sci. J.</span> <span class="volume">57</span>,
            <span class="start-page">293</span>–
            <span class="end-page">302</span> (<span class="year">2009</span>)
            <ul class="cleared">
                <li><a href="http://dx.doi.org/10.1179/136821909X12490326247524">Article</a></li>
            </ul>
        </li>
        """
        ar = HtmlContentExtractor(html_doc)
        print ar.get_summary()

    # @unittest.skip('local test only')
    def test_common_sites_xxx(self):
        logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - [%(asctime)s] %(message)s')
        # ar = legendary_parser_factory('http://codefine.co/%E6%9C%80%E6%96%B0openstack-swift%E4%BD%BF%E7%94%A8%E3%80%81%E7%AE%A1%E7%90%86%E5%92%8C%E5%BC%80%E5%8F%91%E6%89%8B%E5%86%8C/')
        # ar = legendary_parser_factory('http://devo.ps/')
        # ar = legendary_parser_factory('http://services.amazon.com/selling-services/pricing.htm?ld=EL-www.amazon.comAS')
        ar = legendary_parser_factory('http://www.jianshu.com/p/5e997f9b7a9f')
        print ar.get_summary()
        # print ar.article
        # print ar.get_illustration().url
        # print ar.get_favicon_url()

if __name__ == '__main__':
    # basicConfig will only be called automatically when calling
    # logging.debug, logging.info ...
    # calling those method against a logger instance won't apply the basic config
    # see https://docs.python.org/2/library/logging.html#logging.basicConfig
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - [%(asctime)s] %(message)s')
    unittest.main()
