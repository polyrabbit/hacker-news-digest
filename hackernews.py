#coding: utf-8
import re
import logging
from urlparse import urljoin
import urllib2

import os
if 'SERVER_SOFTWARE' not in os.environ:
    os.environ['sae.storage.path'] = '/tmp'
    os.environ['HTTP_HOST'] = 'localhost'

import sae.kvdb
from sae.storage import Bucket
from bs4 import BeautifulSoup as BS
from page_content_extractor import legendary_parser_factory

logger = logging.getLogger(__name__)

kv = sae.kvdb.KVClient()
bucket = Bucket('modern-hacker-news')
bucket.put(metadata={'expires': '1d'})

cookie_support = urllib2.HTTPCookieProcessor()
opener = urllib2.build_opener(cookie_support)
urllib2.install_opener(opener)

class HackerNews(object):
    end_point = 'https://news.ycombinator.com/'

    def __init__(self):
        self.items = []

    def update(self):
        news_list = self.parse_news_list()
        # add new items
        for news in news_list:
            # Use news url as the key
            if not kv.get(news['url']):
                logger.debug("Fetching %s", news['url'])
                article = legendary_parser_factory(news['url'])
                news['summary'] = article.get_summary()
                tm = article.get_top_image()
                if tm:
                    bucket.put_object(tm.url, tm.raw_data, tm.content_type)
                    news['img_id'] = tm.url
                    news['img_src'] = bucket.generate_url(tm.url)
            else:
                logger.debug('Found %s', news['url'])

        # clean up old items
        new_links = frozenset(n['url'] for n in news_list)
        for url, news in kv.get_by_prefix(''):
            if url not in new_links:
                logger.debug('Removing %s', url)
                if 'img_id' in news:
                    bucket.delete_object(news['img_id'])
                kv.delete(url)

    def parse_news_list(self):
        req = urllib2.Request(self.end_point, headers={'User-Agent':
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_0) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/37.0.2062.94 Safari/537.36'})
        dom = BS(urllib2.urlopen(req))
        items = []
        # Sad BS doesn't support nth-of-type(3n)
        for rank, blank_line in enumerate(
                dom.select('table tr table:nth-of-type(2) tr[style="height:5px"]')):
            subtext_dom = blank_line.previous_sibling
            title_dom = subtext_dom.previous_sibling.find('td', class_='title', align=False)

            title = title_dom.a.get_text(strip=True)
            logger.debug('Gotta %s', title)
            url = title_dom.a['href']
            # In case of a discussion on hacker news, such as
            # 9.  Let discuss here
            comhead = title_dom.span and title_dom.span.get_text(strip=True).strip('()') or None

            children_of_subtext_dom = subtext_dom.find('td', class_='subtext').contents
            if len(children_of_subtext_dom) == 1:
                score = \
                author = \
                comment_cnt = \
                comment_url = None
                submit_time = children_of_subtext_dom[0]
            else:
                score = re.search('\d+', children_of_subtext_dom[0].get_text(strip=True)).group()
                author = children_of_subtext_dom[2].get_text()
                submit_time = re.search('\d+ \w+ ago', children_of_subtext_dom[3]).group()
                # In case of no comments yet
                comment_cnt = re.search('\d+', children_of_subtext_dom[4].get_text()) or 0
                comment_url = children_of_subtext_dom[4]['href']

            items.append(dict(
                rank = rank,
                title = title,
                url = urljoin(self.end_point, url),
                comhead = comhead,
                score = score,
                author = author,
                submit_time = submit_time,
                comment_cnt = comment_cnt,
                comment_url = urljoin(self.end_point, comment_url)
            ))
        return items

import unittest

class TestHackerNewsParser(unittest.TestCase):
    def test_parsed_score(self):
        """Every score should be a digit"""
        hn = HackerNews()
        for news in hn.parse_news_list():
            self.assertTrue(news['score'] is None or \
                    news['score'].isdigit())

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - [%(asctime)s] %(message)s')
    # unittest.main()
    hn = HackerNews()
    hn.update()
    for _, news in kv.get_by_prefix(''):
        print news['summary']

