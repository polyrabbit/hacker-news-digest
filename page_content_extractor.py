#coding=utf-8
import re
from urlparse import urljoin
import urllib2
import cStringIO
from PIL import Image
from bs4 import BeautifulSoup as BS, Tag, NavigableString

"""
https://github.com/scyclops/Readable-Feeds/blob/master/readability/hn.py
"""

# Beautifulsoup will convert all tag names to lower-case
ignored_tags = ('option', 'script', 'noscript', 'style', 'iframe')
negative_patt = re.compile(r'comment|combx|disqus|foot|header|menu|rss|'
    'shoutbox|sidebar|sponsor|vote|meta', re.IGNORECASE)
positive_patt = re.compile(r'article|entry|post|column|main|content|'
    'section|text|preview', re.IGNORECASE)

class WebImage(object):
    url = None
    MIN_BYTES_SIZE = 4000
    MAX_BYTES_SIZE = 15*1024*1024
    SCALE_FROM_IMG_TO_TEXT = 22 * 22

    def __init__(self, base_url, img_node):
        if img_node.get('src') is None:
            'fuck me'
        self.base_url = base_url
        self.url = urljoin(base_url, img_node['src'])
        self.img_area_px = self.equivalent_text_len()

    def equivalent_text_len(self):
        height = self.img_node.get('height', '').strip().rstrip('px')
        width = self.img_node.get('width', '').strip().rstrip('px')

        # if you use percentage in height or width,
        # in most cases it cannot be the main-content
        if height.endswith('%') or width.endswith('%'):
            return 0
        try: height = int(height)
        except: height = 0
        try: width = int(width)
        except: width = 0

        if 0 < height <= minpix or 0 < width <= minpix:
            return 0

        if not (height and width):
            fp = cStringIO.stringIO()
            try:
                w, h = Image.open(urllib2.urlope(self.img_node['src'])).size
            except:
                h = w = 1.0
            finally:
                hdw = h/float(w) # we need float here
                if not (height or width):
                    height, width = h, w # no need to convert
                elif not height:
                    height = int(hdw*width)
                else:
                    width = int(hdw*height)
                fp.close()

        if height <= minpix or width <= minpix:
            return 0
        return width * height

    def to_text_len(self):
        return self.img_area_px / self.scale

    def is_candidate_image(self):
        pass

    # See https://github.com/grangier/python-goose
    def is_banner_dimension(self, width, height):
        """
        returns true if we think this is kind of a bannery dimension
        like 600 / 100 = 6 may be a fishy dimension for a good image
        """
        dimension = 1.0 * width / height
        return dimension > 5 or dimension< .2

class HtmlContentExtractor(object):

    def __init__(self, resp):
        self.max_score = -1
        self.article = None # default to an empty doc, if there are no tags.
        charset = resp.info().getparam('charset') # or None
        # what's the more elegent way?
        # dom_tree = BS(cont.replace('<br>', '<br />'), from_encoding=charset)
        doc = BS(resp, from_encoding=charset)

        self.title = doc.title
        self.base_url = resp.geturl()
        self.purge(doc)
        self.calc_best_node(doc)

        # clean ups
        self.clean_up_html()
        self.relative_path2_abs_url()

    def calc_best_node(self, cur_node, depth=0.1):
        text_len = self.text_len(cur_node)
        # img_len = self.img_area_len(cur_node)
        #TODO take image as a factor
        img_len = 0
        impact_factor = self.semantic_effect(cur_node)
        score = (text_len + img_len) * impact_factor * (depth**1.5) # yes 1.5 is a big number
        # cur_node.score = score

        if score > self.max_score:
            self.max_score, self.article = score, cur_node

        for child in cur_node.children: # the direct children, not descendants
            if isinstance(child, Tag):
                self.calc_best_node(child, depth+0.1)

    def semantic_effect(self, node):
        # The most important part
        # returns 1 means no effect
        # 2 means positive
        # .2 means negative
        if isinstance(node, NavigableString):
            return 1

        def _any(iter, func):
            for i in iter:
                if func(i):
                    return True
            return False

        if _any([node.get('id', ''), node.name] + node.get('class', []),
                negative_patt.search):
            return .2

        if _any([node.get('id', ''), node.name] + node.get('class', []),
                positive_patt.search):
            return 2

        return 1

    def text_len(self, cur_node):
        """
        Calc the total the length of text in a node, same as
        sum(len(s) for s in cur_node.stripped_strings)
        """
        # Damn beautifusoup! soup.nonexist will always return None
        if getattr(cur_node, 'text_len', None) is not None:
            return cur_node.text_len
        text_len = 0
        for node in cur_node.children:
            if isinstance(node, Tag):
                text_len += self.text_len(node)
            # Comment is also an instance of NavigableString,
            # so we should not use isinstance(node, NavigableString)
            elif type(node) is NavigableString:
                text_len += len(node.string.strip()) + node.string.count(',')\
                        + node.string.count(u'，')  # Chinese comma
        cur_node.text_len = text_len
        return text_len

    def img_area_len(self, cur_node):
        if getattr(cur_node, 'img_len', None) is not None:
            return cur_node.img_len
        img_len = 0
        if cur_node.name == 'img':
            img_len = WebImage(self.base_url, cur_node).to_text_len()
        else:
            for node in cur_node.find_all('img', recursive=False):  # only search children first
                img_len += self.img_area_len(node)
        cur_node.img_len = img_len
        return img_len

    def purge(self, doc):
        for tname in ignored_tags:
            for d in doc.find_all(tname):
                d.extract()  # decompose calls extract with some more steps
        for style_links in doc.find_all('link', attrs={'type': 'text/css'}):
            style_links.extract()

    def clean_up_html(self):
        for tag in self.article.descendants:
            if isinstance(tag, Tag):
                del tag['class']
                del tag['id']
            # <!-- comment -->
            elif isinstance(tag, NavigableString) and type(tag) is not NavigableString:
                tag.extract()

    def relative_path2_abs_url(self):
        def _rp2au(soup, tp):
            d = {tp: True}
            for tag in soup.find_all(**d):
                tag[tp] = urljoin(self.base_url, tag[tp])
        _rp2au(self.article, 'href')
        _rp2au(self.article, 'src')
        _rp2au(self.article, 'background')

    def get_main_content(self):
        return self.get_article()

    def get_article(self):
        return self.article

    def geturl(self):
        return self.base_url

    def get_title(self):
        return self.title.string

    def get_summary(self):
        pass

# dispatcher
def page_content_parser(url):
    req = urllib2.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; '
        'Intel Mac OS X 10_10_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.94 Safari/537.36'})
    resp  = urllib2.urlopen(req)
    if resp.info().getmaintype() == 'text':
        return HtmlContentExtractor(resp)
    elif resp.info().gettype() == 'application/vnd.ms-excel':
        return excel_parser(resp)
    elif resp.info().gettype() == 'application/msword':
        get_main_content = lambda self : u'再等等，或许下辈子我会看懂<a target="_blank" href="http://download.microsoft.com/download/0/B/E/0_bE8_bDD7-e5_e8-422_a-ABFD-4342_eD7_aD886/Word97-2007_binary_file_format%28doc%29_specification.pdf">word的格式</a>。'
        get_title_prefix = lambda self : u'[DOC]'
        return type('ms_word', (), {'get_main_content':get_main_content, 'get_title_prefix':get_title_prefix})()
    else:
        raise TypeError('I have no idea how the %s is formatted' % resp.info().gettype())

import tempfile

def test_purge():
    html_doc = """
    <html>good<script>whatever</script></html>
    """
    doc = BS(html_doc)
    HtmlContentExtractor.purge.im_func(object(), doc)
    assert doc.find('script') is None

def test_text_len_with_comma():
    html_doc = u"""
    <html>good,，</html>
    """
    with tempfile.NamedTemporaryFile() as fd:
        fd.write(html_doc.encode('utf-8'))
        fd.seek(0)
        resp = urllib2.urlopen('file://%s' % fd.name)
        doc = BS(html_doc, from_encoding='utf-8')
        length = HtmlContentExtractor(resp).text_len(doc)
        assert length == 8

def test_parsing_empty_response():
    html_doc = u"""
    """
    with tempfile.NamedTemporaryFile() as fd:
        fd.write(html_doc.encode('utf-8'))
        fd.seek(0)
        resp = urllib2.urlopen('file://%s' % fd.name)
        assert HtmlContentExtractor(resp).article.text == ''

def test_semantic_affect():
    assert HtmlContentExtractor.semantic_effect.im_func(object(),
            BS('<article>good</article>').article) == 2
    assert HtmlContentExtractor.semantic_effect.im_func(object(),
            BS('<p>good</p>').p) == 1
    assert HtmlContentExtractor.semantic_effect.im_func(object(),
            BS('<p class="conteNt">good</p>').p) == 2
    assert HtmlContentExtractor.semantic_effect.im_func(object(),
            BS('<p class="comment">good</p>').p) == .2

def test_page_extract():
    # e = page_content_parser('http://www.wired.com/2014/09/feds-yahoo-fine-prism/')
    # e = page_content_parser('http://meiriyiwen.com')
    e = page_content_parser('http://youth.dhu.edu.cn/content.asp?id=1951')
    print e.get_article() #.get_text(strip=True, types=(NavigableString,))[:100]

if __name__ == '__main__':
    page_url = 'http://www.infzm.com/content/81698'
    page_url = 'http://meiriyiwen.com/'
    page_url = 'http://cmse.dhu.edu.cn/content_view_ctrl.do?content_iD=5b64ce823b7f7060013b87bcdc590005'
    page_url = 'http://222.204.208.4/pub/model/twogradepage/newsdetail.aspx?id=588&column_id=33'
    # page_url = 'http://youth.dhu.edu.cn/content.asp?id=1947'
    # page_url = 'http://www2.dhu.edu.cn/dhuxxxt/xinwenwang/shownews.asp?id=18824'
    # page_url = 'http://youth.dhu.edu.cn/content.asp?id=1951'
    # page_url = 'http://youth.dhu.edu.cn/content.asp?id=1993'
    # page_url = 'http://www2.dhu.edu.cn/dhuxxxt/xinwenwang/shownews.asp?id=18750'
    # page_url = 'http://www2.dhu.edu.cn/dhuxxxt/xinwenwang/shownews.asp?id=18826'
    # page = page_content_parser(page_url)
    # c =page.get_main_content()
    # print (c.encode('utf-8'))
    test_purge()
    test_text_len_with_comma()
    test_semantic_affect()
    test_parsing_empty_response()
    # test_page_extract()
