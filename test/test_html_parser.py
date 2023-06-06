# coding: utf-8
import os.path
import unittest
from unittest import TestCase

from hacker_news.news import News
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
        html_doc = """
        <html>good,，</html>
        """
        doc = BS(html_doc, features='lxml')
        length = HtmlContentExtractor(html_doc).calc_effective_text_len(doc)
        self.assertEqual(length, 8)

    def test_parsing_empty_response(self):
        html_doc = """
        """
        self.assertEqual(HtmlContentExtractor(html_doc).article.text, '')

    def test_no_content(self):
        html_doc = """
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
        self.assertEqual(page.calc_effective_text_len(page.article), 0)
        self.assertEqual(page.get_content(), '')

    def test_semantic_affect(self):
        # They are static methods
        self.assertTrue(
            HtmlContentExtractor.has_positive_effect(
                BS('<article>good</article>', features='lxml').article))
        self.assertFalse(
            HtmlContentExtractor.has_negative_effect(BS('<p>good</p>', features='lxml').p))
        self.assertFalse(
            HtmlContentExtractor.has_positive_effect(BS('<p>good</p>', features='lxml').p))
        self.assertTrue(
            HtmlContentExtractor.has_positive_effect(
                BS('<p class="conteNt">good</p>', features='lxml').p))
        self.assertTrue(
            HtmlContentExtractor.has_negative_effect(
                BS('<p class="comment">good</p>', features='lxml').p))

    def test_non_top_image(self):
        self.assertIsNone(HtmlContentExtractor('').get_illustration())

    @unittest.skip('Skipped because summary is too short')
    def test_get_content_from_all_short_paragraph(self):
        html_doc = """
        <p>1<h1>2</h1><div>3</div><h1>4</h1></p>
        """
        self.assertEqual(HtmlContentExtractor(html_doc).get_content(), '1 2 3 4')

    def test_get_content_from_short_and_long_paragraph(self):
        html_doc = """
        <h3 class="post-name">HTTP/2: The Long-Awaited Sequel</h3>
        <span class="post-date">Thursday, October 9, 2014 2:01 AM</span>
        <h2>Ready to speed things up? </h2>
        <p>Here at Microsoft, we’re rolling out support in Internet Explorer for the first significant rework of the Hypertext Transfer Protocol since 1999.  It’s been a while, so it’s due.</p>
        <p>While there have been lot of efforts to streamline Web architecture over the years, none have been on the scale of HTTP/2.  We’ve been working hard to help develop this new, efficient and compatible standard as part of the IETF HTTPbis Working Group. It’s called, for obvious reasons, HTTP/2 – and it’s available now, built into the new Internet Explorer starting with the <a href="http://preview.windows.com">Windows 10 Technical Preview</a>.</p>
        """
        self.assertEqual(HtmlContentExtractor(html_doc).get_content(300),
                         '''Here at Microsoft, we’re rolling out support in Internet Explorer for the first significant rework of the Hypertext Transfer Protocol since 1999. It’s been a while, so it’s due.
 While there have been lot of efforts to streamline Web architecture over the years, none have been on the scale of HTTP/2.''')

    def test_get_content_word_cut(self):
        html_doc = '<p>' + '1 ' * 500 + '</p>' + '<p>' + '2 ' * 500 + '</p>'
        summary = HtmlContentExtractor(html_doc).get_content(500)
        self.assertIn('1', summary)
        self.assertNotIn('2', summary)

    @unittest.skip('No preserved tag check for now')
    def test_get_content_with_preserved_tag(self):
        html_doc = '<pre>' + '11 ' * 400 + '</pre>'
        self.assertEqual(html_doc, HtmlContentExtractor(html_doc).get_content(10))
        html_doc = '<pre><code>' + '11\n' * 400 + '</code>' + 'what you think?' * 200 + '</pre>'
        self.assertEqual(HtmlContentExtractor(html_doc).get_content(10),
                         '<pre><code>%s</code></pre>' % '\n'.join(['11'] * 5))

    def test_get_content_with_link_intensive(self):
        html_doc = '<div><p><a href="whatever">' + '1 ' * 500 + '</a></p>' + \
                   '<p>' + '2 ' * 500 + '</p></div>'
        pp = HtmlContentExtractor(html_doc)
        pp.article = BS(html_doc, features='lxml').div
        self.assertTrue(pp.get_content(300).startswith('2 ' * 10))

    def test_escaped_summary(self):
        html_doc = '<code>&lt;a href=&quot;&quot; title=&quot;&quot;&gt; &lt;</code>'
        article = HtmlContentExtractor(html_doc)
        # TODO test longer html
        self.assertEqual(article.get_content(),
                         '&lt;a href=&#34;&#34; title=&#34;&#34;&gt; &lt;')

    def test_no_extra_spaces_between_tags(self):
        html_doc = '<p><strong><span style="color:red">R</span></strong>ed</p>'
        article = HtmlContentExtractor(html_doc)
        self.assertEqual(article.get_content(), 'Red')

    def test_get_content_with_meta_class(self):
        html_doc = '<div><p class="meta">good</p><p>bad</p></div>'
        article = HtmlContentExtractor(html_doc)
        self.assertEqual(article.get_content(4), 'bad')

    def test_get_content_with_nested_div(self):
        html_doc = '<div><div>%s<div>%s</div></div></div>' % ('a ' * 500, 'b ' * 500)
        self.assertTrue(HtmlContentExtractor(html_doc).get_content().startswith('a'))

    def test_empty_title(self):
        """Empty title shouldn't be None"""
        html_doc = '<title></title>'
        article = HtmlContentExtractor(html_doc)
        self.assertEqual(article.title, '')

    def test_cut_content_to_length(self):
        # Test not breaking a sentence in the middle
        html_doc = '<pre>good</pre>'
        self.assertEqual(
            HtmlContentExtractor.cut_content_to_length(BS(html_doc, features='lxml').pre, 1),
            (html_doc, 4))

    def test_cut_content_to_length_break_on_lines(self):
        html_doc = '<pre>good\ngood</pre>'
        self.assertEqual(
            HtmlContentExtractor.cut_content_to_length(BS(html_doc, features='lxml').pre, 1),
            ('<pre>good</pre>', 4))
        html_doc = '<pre><code>good\ngood</code></pre>'
        self.assertEqual(
            HtmlContentExtractor.cut_content_to_length(BS(html_doc, features='lxml').pre, 1),
            ('<pre><code>good</code></pre>', 4))

    def test_cut_content_to_length_with_self_closing_tag(self):
        html_doc = '<pre>good<br>and<img></pre>'
        self.assertEqual(
            HtmlContentExtractor.cut_content_to_length(BS(html_doc, features='lxml').pre, 10),
            ('<pre>good<br/>and<img/></pre>', 7))

    def test_get_content_without_strip(self):
        html_doc = '<div>%s <span>%s</span></div>' % ('a' * 200, 'b' * 200)
        self.assertIn(' ', HtmlContentExtractor(html_doc).get_content())

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
        self.assertEqual('http://local.host/ico.favicon',
                         HtmlContentExtractor(html_doc, 'http://local.host').get_favicon_url())

    def test_clean_up_html_not_modify_iter_while_looping(self):
        with open(os.path.join(
                os.path.abspath(os.path.dirname(__file__)),
                'fixtures/kim.com.html')) as fp:
            html_doc = fp.read()
        try:
            HtmlContentExtractor(html_doc)
        except AttributeError as e:
            self.fail('%s, maybe delete something while looping.' % e)

    def test_CJK(self):
        html_doc = '我' * 1000
        self.assertLess(len(HtmlContentExtractor(html_doc).get_content(100)), 1000)

    def test_tags_separated_by_space(self):
        html_doc = """
        <article><p>Python has a GIL, right? Not quite - PyPy STM is a python implementation
without a GIL, so it can scale CPU-bound work to several cores.
PyPy STM is developed by Armin Rigo and Remi Meier,
and supported by community <em>donations</em>.</p></article>
        """
        a = HtmlContentExtractor(html_doc).get_content(1000)
        self.assertTrue(a
                        .endswith('by community  donations.'))

    @unittest.skip('Only for debug purpose')
    def test_for_debug(self):
        news = News(
            url='https://arstechnica.com/cars/2023/05/automatic-emergency-braking-should-become-mandatory-feds-say/',
            score='15')
        news.pull_content()
        print(news.summary)
        self.assertGreater(len(news.summary), 100)
        self.assertLess(len(news.summary), 500)
