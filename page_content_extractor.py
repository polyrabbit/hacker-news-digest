#coding=utf-8
import re
from urlparse import urljoin
import urllib2
import cStringIO
from PIL import Image
from bs4 import BeautifulSoup as BS, Tag, NavigableString

# Beautifulsoup will convert all tag names to lower-case
candidate_tags = frozenset(['a', 'caption', 'dl', 'dt', 'dd', 'div', 'ol',
    'li', 'ul', 'p', 'pre', 'table', 'tbody', 'thead', 'tfoot', 'tr', 'td', 'br', 'h1', 'h2'])
ignored_tags = ('option', 'script', 'noscript', 'style', 'iframe')
negative_patt = re.compile(r'comment|combx|disqus|foot|header|menu|rss|'
    'shoutbox|sidebar|sponsor|vote|meta', re.IGNORECASE)
positive_patt = re.compile(r'article|entry|post|column|main|content|'
    'section|title|text', re.IGNORECASE)

def is_candidate_tag(node):
    return node.name in candidate_tags
def is_ignored_tag(node):
    return node.name in ignored_tags
def is_positive_node(node):
    return positive_patt.search(node.get('id', '')+''.join(node.get('class', [])))
def is_negative_node(node):
    return node.name == 'a' or negative_patt.search(node.get('id', '')+''.join(node.get('class', [])))

def cut_off(nodes):
    return filter(lambda n: isinstance(n, Tag) and not is_ignored_tag(n), nodes)

class ImgArea(object):

    def __init__(self, bs_node):
        self.bs_node = bs_node      
        self.scale = 22*22
        self.img_area_px = self.calc_area()

    def calc_area(self):
        minpix = 55 # mind the side-bar pics
        height = self.bs_node.get('height', Nothing()).strip().rstrip('px')
        width = self.bs_node.get('width', Nothing()).strip().rstrip('px')

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
                w, h = Image.open(urllib2.urlope(self.bs_node['src'])).size
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
 
class HtmlContentExtractor(object):

    def __init__(self, resp):
        self.max_score = 0
        self.article = Nothing() # if there being no tags, it can return nothing.
        charset = resp.info().getparam('charset') # or None
        # what's the more elegent way?
        # dom_tree = BS(cont.replace('<br>', '<br />'), from_encoding=charset)
        doc = BS(resp, from_encoding=charset)

        self.title = doc.title
        self.base_url = resp.geturl()
        self.purge(doc)
        self.extract(doc)

        # clean ups
        self.clean_up_html()
        self.relative_path2_abs_url()

    def extract(self, cur_node, depth=0.1):
        if is_candidate_tag(cur_node):
            text_len = self.text_len(cur_node)
            img_len = self.img_area_len(cur_node)
            bonus = self.extra_score(cur_node, 'major_len')
            penalty = self.extra_score(cur_node, 'minor_len')
            score = (text_len+img_len-penalty*0.8+bonus)*(depth**1.5) # yes 1.5 is a big number
            # cur_node.score = score

            if score > self.max_score:
                self.max_score, self.article = score, cur_node

        for child in cur_node.children: # the direct children, not descendants
            if isinstance(child, Tag):
                self.extract(child, depth+0.1)

    def extra_score(self, cur_node, len_type='major_len'):
        if isinstance(cur_node, NavigableString):
            return 0
        if getattr(cur_node, len_type, None) is not None:
            return getattr(cur_node, len_type)
        check_tag = is_positive_node if len_type=='major_len' else is_negative_node
        if check_tag(cur_node):
            setattr(cur_node, len_type, self.text_len(cur_node) + self.img_area_len(cur_node))
            return getattr(cur_node, len_type)

        extra_len = 0
        for node in cut_off(cur_node.children):
            if check_tag(node):
                setattr(node, len_type, self.text_len(node) + self.img_area_len(cur_node))
            else:
                self.extra_score(node, len_type)
            extra_len += getattr(node, len_type)
        setattr(cur_node, len_type, extra_len)
        return extra_len

    def text_len(self, cur_node):
        """
        Calc the total the length of text in a node, same as
        sum(len(s) for s in cur_node.stripped_strings)
        """
        if getattr(cur_node, 'text_len', None) is not None:
            return cur_node.text_len
        text_len = 0
        for node in cur_node.children:
            if isinstance(node, Tag) and not is_ignored_tag(node):
                text_len += self.text_len(node)
            # Comment is also an instance of NavigableString,
            # so we should not use isinstance(node, NavigableString)
            elif type(node) is NavigableString:
                text_len += len(node.string.strip())
        cur_node.text_len = text_len
        return text_len

    def img_area_len(self, cur_node):
        if getattr(cur_node, 'img_len', None) is not None:
            return cur_node.img_len
        img_len = 0
        if cur_node.name == 'img':
            img_len = ImgArea(cur_node).to_text_len()
        else:
            for node in cut_off(cur_node.children):
                img_len += self.img_area_len(node)
        cur_node.img_len = img_len
        return img_len

    def purge(self, doc):
        for tname in ignored_tags:
            for d in doc.find_all(tname):
                d.decompose()
        for style_links in doc.find_all('link', attrs={'type': 'text/css'}):
            style_links.decompose()

    def clean_up_html(self):
        trashcan = []
        for tag in self.article.descendants:
            if isinstance(tag, Tag):
                del tag['class']
                del tag['id']
                if tag.name in ignored_tags:
                    trashcan.append(tag)
            elif isinstance(tag, NavigableString) and type(tag) is not NavigableString:
                # tag.extract()
                trashcan.append(tag)

        # map(lambda t: getattr(t, 'decompose', t.extract)(), trashcan)
        [getattr(t, 'decompose', t.extract)() for t in trashcan if t.__dict__]

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

    def get_title_prefix(self):
        return ''

# dispatcher
def page_content_parser(url):
    resp  = urllib2.urlopen(url)
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

def test_purge():
    html_doc = """
    <html>good<script>whatever</script></html>
    """
    doc = BS(html_doc)
    HtmlContentExtractor.purge.im_func(object(), doc)
    assert doc.find('script') is None

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
