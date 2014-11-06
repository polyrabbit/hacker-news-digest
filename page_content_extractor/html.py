#coding: utf-8
import re

import logging
from urlparse import urljoin
from collections import defaultdict
from bs4 import BeautifulSoup as BS, Tag, NavigableString
import requests

import imgsz
from .utils import tokenize, is_paragraph, string_inclusion_ratio
from backports.functools_lru_cache import lru_cache

logger = logging.getLogger(__name__)

# Beautifulsoup will convert all tag names to lower-case
ignored_tags = ('option', 'script', 'noscript', 'style', 'iframe')
negative_patt = re.compile(r'comment|combx|disqus|foot|header|menu|rss|'
    'shoutbox|sidebar|sponsor|vote|meta', re.IGNORECASE)
positive_patt = re.compile(r'article|entry|post|column|main|content|'
    'section|text|preview|view|story-body', re.IGNORECASE)

class WebImage(object):
    is_possible = False
    MIN_PX = 50
    MIN_BYTES_SIZE = 4000
    MAX_BYTES_SIZE = 2.5*1024*1024
    SCALE_FROM_IMG_TO_TEXT = 22*22
    raw_data = ''

    def __init__(self, base_url, img_node):
        # TODO cannot fetch image from washingtonpost
        # e.g. http://www.washingtonpost.com/sf/investigative/2014/09/06/stop-and-seize/
        if img_node.get('src') is None:
            logger.info('No src')
            return
        # see https://bitbucket.org/raphaelzhang/novel-reader/src/d5f1e60c5387bfbc375e89cada55b3b05370cb01/extractor.py#cl-717
        if img_node.get('src').startswith('data:image/'):
            logger.info('Image is encoded in base64, too short')
            return
        if 'avatar' in img_node.get('class', '')+img_node.get('id', '') + img_node.get('src', '').lower():
            logger.info('Maybe this is an avatar(%s)', img_node['src'])
            return
        self.base_url = base_url
        img_node['src'] = urljoin(self.base_url, img_node['src'])
        width, height = self.get_size(img_node)
        # self.img_area_px = self.equivalent_text_len()
        if not (width and height):
            logger.info('Failed no width or height found, %s', img_node['src'])
            return
        if not self.check_dimension(width, height):
            logger.info('Failed on dimension check(width=%s height=%s) %s',
                    width, height, img_node['src'])
            return
        if not self.raw_data:
            self.fetch_img(img_node['src'])
        if not self.check_image_bytesize():
            logger.info('Failed on image_bytesize check, size is %s, %s',
                    len(self.raw_data), img_node['src'])
            return
        self.is_possible = True

    def get_size(self, inode):
        height = inode.get('height', '').strip().rstrip('px')
        width = inode.get('width', '').strip().rstrip('px')
        
        if width.isdigit() and height.isdigit():
            return int(width), int(height)

        if self.fetch_img(inode['src']):
            try:
                return imgsz.fromstring(self.raw_data)[1:]
            except ValueError as e:
                logger.error('Error while determing the size of %s, %s', self.url, e)
                return 0, 0
        return 0, 0

    def fetch_img(self, url):
        try:
            resp = requests.get(url, headers={'Referer': self.base_url})
            # meta info
            self.url = resp.url
            self.raw_data = resp.content
            self.content_type = resp.headers['Content-Type']
            return True
        except (IOError, KeyError) as e:
            logger.info('Failed to fetch img(%s), %s', url, e)
            return False
    
    def to_text_len(self):
        return self.img_area_px / self.scale

    def is_candidate_image(self):
        pass

    # See https://github.com/grangier/python-goose
    def check_dimension(self, width, height):
        """
        returns true if we think this is kind of a bannery dimension
        like 600 / 100 = 6 may be a fishy dimension for a good image
        """
        if width < self.MIN_PX or height < self.MIN_PX:
            return False
        dimension = 1.0 * width / height
        return .2 < dimension < 5

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
    def __init__(self, html, base_url=''):
        # see http://stackoverflow.com/questions/14946264/python-lru-cache-decorator-per-instance
        self.calc_img_area_len = lru_cache(1024)(self.calc_img_area_len)
        self.calc_effective_text_len = lru_cache(1024)(self.calc_effective_text_len)

        self.max_score = -1
        self.scores = defaultdict(int)
        self.text_len_of = defaultdict(int)
        doc = BS(html)

        self.title = doc.title.string if doc.title else u''
        self.base_url = base_url
        self.purge(doc)
        self.article = self.find_main_content(doc)

        # clean ups
        self.clean_up_html()
        self.relative_path2_abs_url()
        # print self.calc_img_area_len.cache_info(), self.calc_effective_text_len.cache_info()

    def set_article_title_point(self, doc, point):
        for parent in self.find_article_header_parents(doc):
            self.scores[parent] = point

    def find_article_header_parents(self, doc):
        # First we give a high point to nodes who have
        # a descendant that is a header tag and matches title most
        def is_article_header(node):
            if re.match(r'h\d+|td', node.name):
                header_txt = node.get_text(separator=u' ', strip=True)
                if string_inclusion_ratio(header_txt, self.title) > .85:
                    return True
            return False

        for node in doc.find_all(is_article_header):
            # Give eligible node a high score
            logger.info('Found a eligible title: %s', node.get_text(separator=u' ', strip=True))
            # self.scores[node] = 1000
            for parent in node.parents:
                if not parent or parent is doc:
                    break
                yield parent

    def set_article_tag_point(self, doc):
        for node in doc.find_all('article'):
            # Double their length
            self.scores[node] += self.calc_effective_text_len(node)

    def calc_node_score(self, node, depth=.1):
        """
        The one with most text is the most likely article, naive and simple
        """
        text_len = self.calc_effective_text_len(node)
        # img_len = self.calc_img_area_len(cur_node)
        #TODO take image as a factor
        img_len = 0
        impact_factor = 2 if self.has_positive_effect(node) else 1
        self.scores[node] += (text_len + img_len) * impact_factor * (depth**1.5)  # yes 1.5 is a big number

        for child in node.children:  # the direct children, not descendants
            if isinstance(child, Tag):
                self.calc_node_score(child, depth+0.1)

    def find_main_content(self, root):
        max_text_len = self.calc_effective_text_len(root)
        self.set_article_title_point(root, max_text_len)  # Give them the highest score
        self.set_article_tag_point(root)

        self.calc_node_score(root)
        article = max(self.scores, key=lambda k: self.scores[k])
        # print self.scores[article], self.scores[root.article]
        logger.info('Score of the main content is %s', self.scores[article])
        return article

    @staticmethod
    def has_positive_effect(node):
        for attr in node.get('id', ''), node.name, ' '.join(node.get('class', [])):
            if positive_patt.search(attr):
                return True
        return False

    @staticmethod
    def has_negative_effect(node):
        for attr in node.get('id', ''), node.name, ' '.join(node.get('class', [])):
            if negative_patt.search(attr):
                return True
        return False

    def calc_effective_text_len(self, node):
        """
        Calc the total the length of text in a child, same as
        sum(len(s) for s in cur_node.stripped_strings)
        """
        text_len = 0
        for child in node.children:
            if isinstance(child, Tag):
                text_len += self.calc_effective_text_len(child)
            # Comment is also an instance of NavigableString,
            # so we should not use isinstance(child, NavigableString)
            elif type(child) is NavigableString:
                text_len += len(child.string.strip()) + child.string.count(',') + \
                            child.string.count(u'，')  # Chinese comma
        if self.has_negative_effect(node):
            return text_len * .2
        return text_len

    def calc_img_area_len(self, cur_node):
        img_len = 0
        if cur_node.name == 'img':
            img_len = WebImage(self.base_url, cur_node).to_text_len()
        else:
            for node in cur_node.find_all('img', recursive=False):  # only search children first
                img_len += self.calc_img_area_len(node)
        return img_len

    def purge(self, doc):
        for tname in ignored_tags:
            for d in doc.find_all(tname):
                d.extract()  # decompose calls extract with some more steps
        for style_links in doc.find_all('link', attrs={'type': 'text/css'}):
            style_links.extract()

    def clean_up_html(self):
        trashcan = []
        for tag in self.article.descendants:
            if isinstance(tag, Tag):
                del tag['class']
                del tag['id']
            # <!-- comment -->
            elif isinstance(tag, NavigableString) and type(tag) is not NavigableString:
                # Definitely should not modify the iter while looping
                # tag.extract()
                trashcan.append(tag)
        for t in trashcan:
            t.extract()

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

    def get_summary(self, max_length=300):

        block_elements = ['article', 'div', 'p', 'pre', 'blockquote', 'cite', 'section',
                'code', 'input', 'legend', 'tr', 'th', 'textarea', 'thead', 'tfoot']
        preserved_tags = {'code'}

        def link_intensive(node):
            all_text = len(node.get_text(separator=u'', strip=True, types=(NavigableString,)))
            if not all_text:
                return False
            link_text = 0
            for a in node.find_all('a'):
                link_text += len(a.get_text(separator=u'', strip=True, types=(NavigableString,)))
            return float(link_text) / all_text >= .5

        parents = set(self.find_article_header_parents(self.article))
        def deepest_block_element_first_search(node):
            # TODO tooooo inefficient
            for p in node.find_all(block_elements):
                if p.founded:
                    continue
                if p in parents:
                    continue
                p.founded = True
                if not p.find(block_elements):
                    if link_intensive(p):
                        continue
                    if p.name in preserved_tags:
                        yield unicode(p)
                    else:
                        yield p.get_text(separator=u'', strip=True, types=(NavigableString,))
                else:
                    for grand_p in deepest_block_element_first_search(p):
                        yield grand_p
            if not node.find(block_elements):  # TODO tooooooo redundant
                if node.name in block_elements and not link_intensive(node):
                    if node.name in preserved_tags:
                        yield unicode(node)
                    else:
                        yield node.get_text(separator=u'', strip=True, types=(NavigableString,))

        partial_summaries = []
        len_of_summary = 0
        for p in deepest_block_element_first_search(self.article):
            if len(tokenize(p)) > 20:  # consider it to be a paragraph
                # A tag should be considered atom
                p_mat = re.search(r'<([a-z]+)[^>]*>([^<]*)</\1>', p)
                if p_mat:
                    partial_summaries.append(p)
                    len_of_summary += len(p_mat.group(2))
                    if len_of_summary > max_length:
                        return ''.join(partial_summaries)
                else:
                    if len_of_summary + len(p) > max_length:
                        for word in tokenize(p):
                            partial_summaries.append(word)
                            len_of_summary += len(word)
                            if len_of_summary > max_length:
                                partial_summaries.append('...')
                                return ''.join(partial_summaries)
                    else:
                        partial_summaries.append(p)
                        len_of_summary += len(p)
                partial_summaries.append(' ')

        if partial_summaries:
            return ''.join(partial_summaries)
        logger.info('Nothing qualifies a paragraph, get a jam')
        text = self.article.get_text(separator=u' ', strip=True, types=(NavigableString,))
        return text[:max_length]+' ...' if len(text) > max_length else text

    def get_top_image(self):
        for img_node in self.article.find_all('img'):
            img = WebImage(self.base_url, img_node)
            if img.is_possible:
                logger.info('Found a top image %s', img.url)
                return img
        return None

