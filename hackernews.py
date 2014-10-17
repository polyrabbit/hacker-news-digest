#coding: utf-8
import re
import logging
from urlparse import urljoin, urlsplit

from bs4 import BeautifulSoup as BS
from page_content_extractor import legendary_parser_factory

logger = logging.getLogger(__name__)

from config import sites_for_users, summary_length
from db import ImageStorage, HnStorage
import requests

class HackerNews(object):
    end_point = 'https://hacker-news.firebaseio.com/v0/{uri}'
    storage_class = HnStorage

    def __init__(self):
        self.storage = self.storage_class()
        self.im_storage = ImageStorage()
        self.s = requests.Session()

    def update(self, force=False):
        if force:
            self.storage.remove_except([])
        news_list = self.get_news_list()
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
                    news['summary'] = parser.get_summary(summary_length)
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

    def get_news_list(self):
        # TODO tooooo damn slow, try use a generator here
        items = []
        ids = self.s.get(self.end_point.format(uri='topstories.json')).json()[:30]
        for rank, item_id in enumerate(ids):
            try:
                item = self.s.get(self.end_point.format(uri='item/%s.json' % item_id)).json()
                item['comment_url'] = self.build_comment_link(item_id)
            except requests.exceptions.RequestException as e:
                logger.error('An exception occurred while trying to fetch story %s, %s',
                                 self.end_point.format(uri='item/%s.json' % item_id), e)
                continue
            logger.info('Gotta "%s"', item['title'])
            item['rank'] = rank
            item['comhead'] = self.parse_comhead(item['url']) if item['url'] else None
            # Come after comhead
            item['url'] = item['url'] or self.build_comment_link(item_id)
            item['author'] = item.get('by')
            item['author_link'] = self.build_user_link(item.get('by'))
            item['submit_time'] = item.get('time')
            item['comment_cnt'] = self.get_comment_cnt(item.get('kids', []))
            items.append(item)
        return items

    def parse_comhead(self, url):
        if not url:
            return None
        if not url.startswith('http'):
            url = 'http://' + url
        us = urlsplit(url.lower())
        comhead = us.hostname
        hs = comhead.split('.')
        if len(hs)>2 and hs[0] == 'www':
            comhead = comhead[4:]
        if comhead.endswith(sites_for_users):
            ps = us.path.split('/')
            if len(ps)>1 and ps[1]:
                comhead = '%s/%s' % (comhead, ps[1])
        return comhead

    def build_user_link(self, uid):
        if not uid:
            return None
        return 'https://news.ycombinator.com/user?id=%s' % uid

    def build_comment_link(self, item_id):
        if not item_id:
            return None
        return 'https://news.ycombinator.com/item?id=%s' % item_id

    def get_comment_cnt(self, kids):

        def get_children(node_id):
            try:
                return self.s.get(self.end_point.format(uri='item/%s.json' %
                    node_id)).json().get('kids', [])
            except requests.exceptions.RequestException as e:
                logger.error('An exception occurred while trying to fetch comment %s, %s',
                                 self.end_point.format(uri='item/%s.json' % node_id), e)
                return []

        def get_descendant_cnt(node_id):
            children = get_children(node_id)
            cnt = len(children)
            for c in children:
                cnt += get_descendant_cnt(c)
            return cnt

        return sum(map(get_descendant_cnt, kids)) + len(kids)

    def get_all(self):
        return self.storage.get_all()

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - [%(asctime)s] %(message)s')
    # unittest.main()
    hn = HackerNews()
    print hn.get_all()

