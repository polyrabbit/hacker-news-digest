#coding: utf-8
import re
import logging
from urlparse import urljoin, urlsplit

from bs4 import BeautifulSoup as BS
from null import Null
from page_content_extractor import legendary_parser_factory

logger = logging.getLogger(__name__)

from config import sites_for_users, summary_length
import models
import requests

class HackerNews(object):
    end_point = 'https://news.ycombinator.com/'
    model_class = models.HackerNews

    def update(self, force=False):
        stats = {'updated': 0, 'added': 0, 'errors': []}
        if force:
            self.model_class.remove_except([])
        news_list = self.parse_news_list()
        # add new items
        for news in news_list:
            try:
                # Use news url as the key
                if self.model_class.query.get(news['url']):
                    logger.info('Updating %s', news['url'])
                    stats['updated'] += 1
                    # We need the url so we can't pop it here
                    _news = news.copy()
                    self.model_class.update(_news.pop('url'), **_news)
                else:
                    logger.info("Fetching %s", news['url'])
                    try:
                        parser = legendary_parser_factory(news['url'])
                        news['summary'] = parser.get_summary(summary_length)
                        news['favicon'] = parser.get_favicon_url()
                        tm = parser.get_illustration()
                        if tm:
                            img_id = models.Image.add(content_type=tm.content_type,
                                    raw_data=tm.raw_data)
                            news['img_id'] = img_id
                    except Exception as e:
                        logger.exception('Failed to fetch %s, %s', news['url'], e)
                        stats['errors'].append(str(e))
                    self.model_class.add(**news)
                    stats['added'] += 1
            except Exception as e:
                logger.exception(e)
                stats['errors'].append(str(e))

        if not force:
            # clean up old items
            self.model_class.remove_except([n['url'] for n in news_list])
        return stats

    def parse_news_list(self):
        dom = BS(requests.get(self.end_point).text)
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


            # pop up user first, so everything left has a pattern
            author_dom = (subtext_dom.find('a', href=re.compile(r'^user', re.I)) or Null).extract()
            author = author_dom.text.strip() or None
            author_link = author_dom['href'] or None
            score_human = subtext_dom.find(text=re.compile('\d+ points')) or '0'
            score = re.search('\d+', score_human).group() or None
            submit_time = subtext_dom.find(text=re.compile('\d+ \w+ ago')) or None
            # In case of no comments yet
            comment_dom = subtext_dom.find('a', text=re.compile('\d+ comments')) or Null
            comment_cnt = re.search('\d+', comment_dom.get_text() or '0').group()
            comment_url = self.get_comment_url(comment_dom['href'])

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
                comment_url = comment_url
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
        if comhead.endswith(sites_for_users):
            ps = us.path.split('/')
            if len(ps)>1 and ps[1]:
                comhead = '%s/%s' % (comhead, ps[1])
        return comhead

    def get_comment_url(self, path):
        if not isinstance(path, basestring):
            return None
        return 'http://cheeaun.github.io/hackerweb/#/item/%s' % re.search(r'\d+', path).group()

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - [%(asctime)s] %(message)s')
    # unittest.main()
    hn = HackerNews()
    hn.update()

