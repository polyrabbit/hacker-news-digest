# coding: utf-8
import os.path
import unittest
from unittest import TestCase

from hacker_news.news import News
from page_content_extractor import parser_factory
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
        parser = HtmlContentExtractor('')
        self.assertTrue(
            parser.has_positive_effect(
                BS('<article>good</article>', features='lxml').article))
        self.assertFalse(
            parser.has_negative_effect(BS('<p>good</p>', features='lxml').p))
        self.assertFalse(
            parser.has_positive_effect(BS('<p>good</p>', features='lxml').p))
        self.assertTrue(
            parser.has_positive_effect(
                BS('<p class="conteNt">good</p>', features='lxml').p))
        self.assertTrue(
            parser.has_negative_effect(
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

    def test_donot_summarize_code_block(self):
        html_doc = '''<p>What am I talking about here? Consider the <code>std::fmt::Display</code> trait.</p>
<pre data-lang="Rust" style="background-color:#282828;color:#fdf4c1aa;" class="language-Rust "><code class="language-Rust" data-lang="Rust"><span style="color:#fa5c4b;">pub trait </span><span style="color:#8ec07c;">Display </span><span>{
</span><span>    </span><span style="font-style:italic;color:#928374;">// Required method
</span><span>}'''
        page = HtmlContentExtractor(html_doc)
        self.assertEqual(page.get_content(), 'What am I talking about here? Consider the std::fmt::Display trait.')

    def test_get_content_with_link_intensive(self):
        html_doc = '<div><p><a href="whatever">' + '1 ' * 500 + '</a></p>' + \
                   '<p>' + '2 ' * 500 + '</p></div>'
        pp = HtmlContentExtractor(html_doc)
        pp.article = BS(html_doc, features='lxml').div
        self.assertTrue(pp.get_content(300).startswith('2 ' * 10))

    def test_pre_tag_in_maillist_sites(self):
        mail = '''I promised a post-mortem three weeks ago after I brought the Tarsnap service
back online. It took me an unforgivably long time to get around to writing
this, but here it is.'''
        html_doc = f'''<pre style="margin: 0em;">
        {mail}
        </pre>'''
        page = HtmlContentExtractor(html_doc)
        self.assertEqual(page.get_content(), mail)

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
        a = HtmlContentExtractor(html_doc).get_content()
        self.assertTrue(a.endswith('by community donations.'))

    def test_ask_hn_include_content(self):
        parser = parser_factory('https://news.ycombinator.com/item?id=36317509')
        content = parser.get_content()
        self.assertTrue(content.startswith('I have expertise in web backend and infrastructure development, '))
        self.assertTrue(content.endswith('I would love to hear it.'))

    def test_arxiv_content(self):
        parser = parser_factory('https://arxiv.org/abs/2306.07695')
        content = parser.get_content()
        self.assertTrue(content.startswith('Short Message Service'))
        self.assertTrue(content.endswith('network architecture.'))

    def test_link_intensive_wikipedia(self):
        parser = parser_factory('https://en.wikipedia.org/wiki/Google_Sidewiki')
        content = parser.get_content()
        self.assertTrue(content.startswith('Google Sidewiki was a web annotation tool from Google'), msg=content[:100])

    def test_dynamic_js_page(self):
        parser = parser_factory('https://www.science.org/content/article/u-s-wants-change-how-researchers-get-access-huge-trove-health-data-many-don-t-idea')
        content = parser.get_content()
        self.assertTrue(content.startswith('Health researchers'), msg=content[:100])

    def test_longer_meta_description(self):
        html_doc = """
        <meta property="og:description" content="aaaa" />
        <meta name="twitter:description" content="bbb" />
        """
        parser = HtmlContentExtractor(html_doc)
        self.assertEqual(parser.get_meta_description(), "aaaa")

    def test_need_escape_unsafe_meta_description(self):
        content = "The upload handler checks that the content type starts with &quot;image/&quot;, but this check includes the image/svg+xml content type, so the following image is accepted: &lt;?xml version=&quot;1.0&quot; encoding=&quot;UTF-8&quot; standalone=&quot;no&quot;?&gt; &lt;svg xmlns=&quot;http://w..."
        html_doc = f"""
        <meta name="description" content="{content}">
        """
        parser = HtmlContentExtractor(html_doc)
        # &quot; == &#34;
        self.assertEqual(parser.get_meta_description(), content.replace('&quot;', '&#34;'))

    def test_get_all_meta_images(self):
        src = 'https://opengraph.githubassets.com/740568cb37e42d5beb5c65378e1f66a0a72e5cb1650c8a45df4466e9472825a2/tikv/agatedb'
        html_doc = f"""
        <meta name="twitter:image:src" content="{src}" />
        <meta property="og:image" content="{src}" />
        <meta name="twitter:image" content="{src}" />
        <meta property="og:image:alt" content=":newspaper:" />
        """
        parser = HtmlContentExtractor(html_doc)
        self.assertEqual([src, src, src], parser.get_meta_image())

    def test_no_double_punish_on_negative_node(self):
        html_doc = f"""
        <div>
        <foot>
        <h1>{'a'*10}</h1>
        </foot>
        </div>
        """
        parser = HtmlContentExtractor(html_doc)
        self.assertEqual(2, parser.calc_effective_text_len(parser.doc.find('h1')))  # positive
        self.assertEqual(2, parser.calc_effective_text_len(parser.doc.find('foot')))  # negative
        self.assertEqual(2, parser.calc_effective_text_len(parser.doc.find('div')))  # positive

    @unittest.skip('Only for debug purpose')
    def test_for_debug(self):
        news = News(
            # url='https://infinitemac.org/',
            # url='https://www.leviathansecurity.com/blog/tunnelvision',
            # url='https://voidstarsec.com/blog/jtag-pifex',
            url='https://yosefk.com/blog/a-100x-speedup-with-unsafe-python.html',
            score=config.openai_score_threshold + 1)
        news.pull_content()
        print(news.summary)
        self.assertGreater(len(news.summary), 100)
        self.assertLess(len(news.summary), 500)
