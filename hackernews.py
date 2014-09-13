#coding: utf-8
import urllib2
from bs4 import BeautifulSoup as BS, Tag, NavigableString

class HackerNewsItem(object):
    title = None
    url = None
    comhead = None
    score = None
    author = None
    last_update = None
    comment_cnt = None
    comment_url = None

class HackerNews(object):
    end_point = 'https://news.ycombinator.com/'

    def update(self):
        req = urllib2.Request(self.end_point, headers={'User-Agent':
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_0) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/37.0.2062.94 Safari/537.36'})
        dom = BS(urllib2.urlopen(req))
