# coding: utf-8
import logging
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup as BS
from null import Null

from config import sites_for_users
from hacker_news.news import News
from page_content_extractor import ParseError
from page_content_extractor.http import session

logger = logging.getLogger(__name__)


def parse_site(url):
    if not url.startswith('http'):
        url = 'http://' + url
    us = urlsplit(url.lower())
    comhead = us.hostname
    hs = comhead.split('.')
    if len(hs) > 2 and hs[0] == 'www':
        comhead = comhead[4:]
    if comhead in sites_for_users:
        ps = us.path.split('/')
        if len(ps) > 1 and ps[1]:
            comhead = '%s/%s' % (comhead, ps[1])
    return comhead


class HackerNewsParser(object):
    end_point = 'https://news.ycombinator.com/'

    def parse_news_list(self):
        resp = session.get(self.end_point)
        resp.raise_for_status()
        content = resp.text
        dom = BS(content, features="lxml")
        items = []
        for rank, item_line in enumerate(
                dom.select('table tr table tr.athing')):
            # previous_sibling won't work when there are spaces between them.
            subtext_dom = item_line.find_next_sibling('tr')
            title_dom = item_line.find('td', class_='title', align=False)

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
            score_human = subtext_dom.find(string=re.compile(r'\d+.+point')) or '0'
            score = re.search(r'\d+', score_human).group() or None
            submit_time = subtext_dom.find(string=re.compile(r'\d+ \w+ ago')) or None
            if submit_time:
                submit_time = self.human2datetime(submit_time)
            # In case of no comments yet
            comment_dom = subtext_dom.find('a', string=re.compile(r'\d+.+comment')) or Null
            discuss_dom = subtext_dom.find('a', string=re.compile(r'discuss')) or Null
            comment_cnt = re.search(r'\d+', comment_dom.get_text() or '0').group()
            comment_url = self.get_comment_url(comment_dom['href']) or self.get_comment_url(discuss_dom['href'])

            items.append(News(
                rank=rank,
                title=title,
                url=url,
                comhead=comhead,
                score=score,
                author=author,
                author_link=urljoin(self.end_point, author_link) if author_link else None,
                submit_time=submit_time,
                comment_cnt=comment_cnt,
                comment_url=comment_url
            ))
        if len(items) == 0:
            raise ParseError('failed to parse hacker news page, got 0 item, text %s' % content)
        return items

    def parse_comhead(self, url):
        return parse_site(url)

    def get_comment_url(self, path):
        if not isinstance(path, str):
            return None
        return 'https://news.ycombinator.com/item?id=%s' % re.search(r'\d+', path).group()

    def human2datetime(self, text):
        """Convert human readable time strings to datetime
        >>> self.human2datetime('2 minutes ago')
        datetime.datetime(2015, 11, 1, 14, 42, 24, 910863)

        """
        day_ago = hour_ago = minute_ago = 0
        m = re.search(r'(?P<day>\d+) day', text, re.I)
        if m:
            day_ago = int(m.group('day'))
        m = re.search(r'(?P<hour>\d+) hour', text, re.I)
        if m:
            hour_ago = int(m.group('hour'))
        m = re.search(r'(?P<minute>\d+) minute', text, re.I)
        if m:
            minute_ago = int(m.group('minute'))
        return datetime.utcnow() - \
            timedelta(days=day_ago, hours=hour_ago, minutes=minute_ago)
