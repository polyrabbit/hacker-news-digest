#coding: utf-8
import re
import logging
from urlparse import urljoin, urlsplit
import urllib2

from bs4 import BeautifulSoup as BS
from page_content_extractor import legendary_parser_factory

logger = logging.getLogger(__name__)

from db import ImageStorage, HnStorage

cookie_support = urllib2.HTTPCookieProcessor()
opener = urllib2.build_opener(cookie_support)
urllib2.install_opener(opener)

class HackerNews(object):
    end_point = 'https://news.ycombinator.com/'
    storage_class = HnStorage

    def __init__(self):
        self.storage = self.storage_class()
        self.im_storage = ImageStorage()

    def update(self):
        news_list = self.parse_news_list()
        # add new items
        for news in news_list:
            # Use news url as the key
            if self.storage.exist(news['url']):
                logger.info('Updating %s', news['url'])
                # We need the url so we can't pop it here
                _news = news.copy()
                self.storage.update(pk=_news.pop('url'), **_news)
            else:
                logger.info("Fetching %s", news['url'])
                try:
                    parser = legendary_parser_factory(news['url'])
                    news['summary'] = parser.get_summary()
                    tm = parser.get_top_image()
                    if tm:
                        img_id = self.im_storage.put(raw_data=tm.raw_data,
                                content_type=tm.content_type)
                        news['img_id'] = img_id
                except Exception:
                    logger.exception('Failed to fetch %s', news['url'])
                self.storage.put(**news)

        # clean up old items
        self.storage.remove_except([n['url'] for n in news_list])

    def parse_news_list(self):
        req = urllib2.Request(self.end_point, headers={'User-Agent':
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_0) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/37.0.2062.94 Safari/537.36'})
        resp = urllib2.urlopen(req)
        dom = BS(resp, from_encoding=resp.info().getparam('charset'))
        items = []
        # Sad BS doesn't support nth-of-type(3n)
        for rank, blank_line in enumerate(
                dom.select('table tr table:nth-of-type(2) tr[style="height:5px"]')):
            # previous_sibling won't work when there are spaces between them.
            subtext_dom = blank_line.find_previous_sibling('tr')
            title_dom = subtext_dom.find_previous_sibling('tr').find('td', class_='title', align=False)

            title = title_dom.a.get_text(strip=True)
            logger.info('Gotta %s', title)
            url = urljoin(self.end_point, title_dom.a['href'])
            # In case of a discussion on hacker news, such as
            # 9.  Let discuss here
            # comhead = title_dom.span and title_dom.span.get_text(strip=True).strip('()') or None
            comhead = self.parse_comhead(url)

            children_of_subtext_dom = subtext_dom.find('td', class_='subtext').contents
            if len(children_of_subtext_dom) == 1:
                score = \
                author = \
                author_link = \
                comment_cnt = \
                comment_url = None
                submit_time = re.search('\d+ \w+ ago', children_of_subtext_dom[0]).group()
            else:
                score = re.search('\d+', children_of_subtext_dom[0].get_text(strip=True)).group()
                author = children_of_subtext_dom[2].get_text()
                author_link = children_of_subtext_dom[2]['href']
                submit_time = re.search('\d+ \w+ ago', children_of_subtext_dom[3]).group()
                # In case of no comments yet
                comment_cnt = (re.search('\d+', children_of_subtext_dom[4].get_text())
                        or re.search('0', '0')).group()
                comment_url = children_of_subtext_dom[4]['href']

            items.append(dict(
                rank = rank,
                title = title,
                url = url,
                comhead = comhead,
                score = score,
                author = author,
                author_link = urljoin(self.end_point, author_link)  if author_link else None,
                submit_time = submit_time,
                comment_cnt = comment_cnt,
                comment_url = urljoin(self.end_point, comment_url) if comment_url else None
            ))
        return items

    def parse_comhead(self, url):
        if not url.startswith('http'):
            url = 'http://' + url
        us = urlsplit(url.lower())
        comhead = us.hostname
        hs = comhead.split('.')
        if len(hs)>2 and hs[0] == 'www':
            comhead = comhead[4:]
        if comhead.endswith('github.com'):
            ps = us.path.split('/')
            if len(ps)>1 and ps[1]:
                comhead = '%s/%s' % (comhead, ps[1])
        return comhead

    def get_all(self):
        return self.storage.get_all()

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - [%(asctime)s] %(message)s')
    # unittest.main()
    hn = HackerNews()
    hn.update()

