#coding: utf-8
import re
import logging
from urlparse import urljoin
import urllib2
from bs4 import BeautifulSoup as BS, Tag, NavigableString

import imgsz

logger = logging.getLogger(__name__)

# Beautifulsoup will convert all tag names to lower-case
ignored_tags = ('option', 'script', 'noscript', 'style', 'iframe')
negative_patt = re.compile(r'comment|combx|disqus|foot|header|menu|rss|'
    'shoutbox|sidebar|sponsor|vote|meta', re.IGNORECASE)
positive_patt = re.compile(r'article|entry|post|column|main|content|'
    'section|text|preview', re.IGNORECASE)

class WebImage(object):
    is_possible = False
    MIN_BYTES_SIZE = 4000
    MAX_BYTES_SIZE = 15*1024*1024
    SCALE_FROM_IMG_TO_TEXT = 22*22

    def __init__(self, base_url, img_node):
        if img_node.get('src') is None:
            logger.debug('No src')
            return
        self.base_url = base_url
        width, height = self.get_size(img_node)
        # self.img_area_px = self.equivalent_text_len()
        if not (width and height):
            return
        if self.is_banner_dimension(width, height):
            logger.debug('Failed on is_banner_dimension check')
            return
        if not self.check_image_bytesize():
            logger.debug('Failed on image_bytesize check')
            return
        self.is_possible = True

    def get_size(self, inode):
        height = inode.get('height', '').strip().rstrip('px')
        width = inode.get('width', '').strip().rstrip('px')
        
        if width.isdigit() and height.isdigit():
            return int(width), int(height)

        url = urljoin(self.base_url, inode['src'])
        try:
            resp = urllib2.urlopen(self.build_request(url))
            # meta info
            self.url = url
            self.raw_data = resp.read()
            self.content_type = resp.info.getmaintype()
            return imgsz.fromstring(self.raw_data)[1:]
        except IOError as e:
            logger.debug(e)
            return 0, 0
    
    def build_request(self, url):
        return urllib2.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; '
                'Intel Mac OS X 10_10_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.94 Safari/537.36',
                'Referer': self.base_url})

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

    def check_image_bytesize(self):
        return self.MIN_BYTES_SIZE < len(self.raw_data) < self.MAX_BYTES_SIZE

    def save(self, fp):
        if isinstance(fp, basestring):
            fp = open(fp, 'wb')
        fp.write(self.raw_data)
        fp.close()

class HtmlContentExtractor(object):
    """
    see https://github.com/scyclops/Readable-Feeds/blob/master/readability/hn.py
    """
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

    def get_summary(self, head=200):
        first_header = self.article.find(name=re.compile(r'h\d'))
        if first_header:
            first_header.extract()
        return self.article.get_text(strip=True, types=(NavigableString,))[:head]

    def get_top_image(self):
        for img_node in self.article.find_all('img'):
            img = WebImage(self.base_url, img_node)
            if img.is_possible:
                return img
        return None

