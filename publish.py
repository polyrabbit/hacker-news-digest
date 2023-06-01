import json
import logging
import os
import pathlib
from datetime import datetime, date
from hashlib import md5
from urllib.parse import urlparse

from ago import human
from feedwerk.atom import AtomFeed
from jinja2 import Environment, FileSystemLoader, filters

import config
from news_parser import HackerNewsParser
from page_content_extractor import parser_factory

logger = logging.getLogger(__name__)


def natural_datetime(dt, precisoin):
    # We use utc timezone because dt is in utc
    return human(datetime.utcnow() - dt, precisoin)


def elapsed(dt):
    return (datetime.utcnow() - dt).total_seconds() * 1000


output_dir = os.path.join(os.path.dirname(__file__), "output/")
environment = Environment(
    loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates/")), autoescape=True)
environment.filters["natural_datetime"] = natural_datetime
environment.filters["elapsed"] = elapsed
environment.globals["disable_ads"] = 'DISABLE_ADS' in os.environ


class Summary(str):
    def short(self):
        if not self:
            return ''
        if self.startswith('<iframe'):
            return self
        return filters.do_truncate(environment, self.strip(), length=300, end=' ...')


def amend_news(news):
    try:
        logger.info("Fetching %s", news['url'])
        parser = parser_factory(news['url'])
        news['summary'] = Summary(parser.get_summary(config.summary_length))
        news['favicon'] = parser.get_favicon_url()
        tm = parser.get_illustration()
        if tm:
            fname = md5(tm.raw_data).hexdigest()
            fname += pathlib.Path(urlparse(tm.url).path).suffix
            tm.save(os.path.join(output_dir, "image", fname))
            news['image'] = tm
            news['img_id'] = fname
    except Exception as e:
        logger.exception('Failed to fetch %s, %s', news['url'], e)


# Generate github pages
def gen_page(news_list):
    template = environment.get_template("hackernews.html")
    static_page = os.path.join(output_dir, "index.html")
    rendered = template.render(news_list=news_list, last_updated=datetime.utcnow())
    with open(static_page, "w") as fp:
        fp.write(rendered)
    logger.info('Written %d bytes to %s', len(rendered), static_page)


def gen_feed(news_list):
    feed = AtomFeed('Hacker News Digest',
                    updated=datetime.utcnow(),
                    feed_url='http://hackernews.betacat.io/feed.xml',
                    url='http://hackernews.betacat.io',
                    author={
                        'name': 'polyrabbit',
                        'uri': 'https://github.com/polyrabbit/'}
                    )
    for news in news_list:
        summary_text = ''
        if 'summary' in news and news['summary'] is not None:
            summary_text = news['summary'].short()
        feed.add(news['title'],
                 content='%s%s%s' % (('<img src="%s" style="width: 220px; float: left" />' % news[
                     'image'].url if 'image' in news and news['image'].url  # not None
                                      else ''), summary_text, (
                                         ' <a href="%s" target="_blank">[comments]</a>' % news[
                                             'comment_url'] if 'comment_url' in news and news[
                                             'comment_url'] else '')),
                 author={
                     'name': news['author'],
                     'uri': news['author_link']
                 } if news['author_link'] else (),
                 url=news['url'],
                 updated=news['submit_time'], )
    rendered = feed.to_string()
    output_path = os.path.join(output_dir, "feed.xml")
    with open(output_path, "w") as fp:
        fp.write(rendered)
    logger.info('Written %d bytes to %s', len(rendered), output_path)


def gen_json(news_list):
    news_map = dict(map(lambda n: (n.get('url', ''), n.get('summary', '')), news_list))

    def json_serial(obj):
        """JSON serializer for objects not serializable by default json code"""
        if isinstance(obj, (datetime, date)):
            return int(obj.timestamp())
        raise TypeError("Type %s not serializable" % type(obj))

    rendered = json.dumps(news_map, default=json_serial)
    output_path = os.path.join(output_dir, "summary.json")
    with open(output_path, "w") as fp:
        fp.write(rendered)
    logger.info('Written %d bytes to %s', len(rendered), output_path)


if __name__ == "__main__":
    hn = HackerNewsParser()
    news_list = hn.parse_news_list()
    for news in news_list:
        amend_news(news)
    gen_page(news_list)
    gen_feed(news_list)
