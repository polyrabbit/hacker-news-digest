import argparse
import logging
import os
import time
from datetime import datetime
from urllib.parse import urljoin

from feedwerk.atom import AtomFeed
from jinja2 import Environment, FileSystemLoader, filters

import config
import db.translation
from db import image
from hacker_news.algolia_api import get_daily_news
from hacker_news.parser import HackerNewsParser

logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(description='Generate hacker news static page')
parser.add_argument("page", choices=['home', 'daily'], help="Specify page to generate (home or daily)")
args = parser.parse_args()


def translate(text, lang):
    return db.translation.get(text, lang)


def truncate(text):
    return filters.do_truncate(environment, text,
                               length=config.summary_size,
                               end=' ...')


environment = Environment(
    loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates/")), autoescape=True)
environment.filters["translate"] = translate
environment.filters["truncate"] = truncate
environment.globals["config"] = config


def gen_frontpage():
    hn = HackerNewsParser()
    news_list = hn.parse_news_list()
    for news in news_list:
        news.pull_content()
    gen_page(news_list, 'index.html', 'en')
    gen_page(news_list, 'zh.html', 'zh')
    gen_feed(news_list)


def gen_daily():
    # yesterday = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    # yesterday_summary = os.path.join(config.output_dir, f'daily/{yesterday.strftime("%Y-%m-%d")}/index.html')
    # rand = random.random()
    # if not os.path.exists(yesterday_summary):
    #     logger.info(f'Generating a fresh daily page as {yesterday_summary} does not exist')
    # elif rand > 0.3:
    #     logger.info(f'Will not generate daily page this time, rand {rand}')
    #     return
    # else:
    logger.info(f'Will refresh daily page for the past {config.updatable_within_days} days')
    daily_items = get_daily_news(config.updatable_within_days)
    for date, items in daily_items.items():
        for i, item in enumerate(items):
            item.rank = i
            item.pull_content()
        gen_page(items, f'daily/{date.strftime("%Y-%m-%d")}/index.html')


# Generate GitHub pages
def gen_page(news_list, path, lang='en'):
    if not news_list:
        return  # no overwrite
    template = environment.get_template('hackernews.html')
    static_page = os.path.join(config.output_dir, path)
    directory = os.path.dirname(static_page)
    os.makedirs(directory, exist_ok=True)
    start = time.time()
    daily_links = get_daily_links()
    rendered = template.render(news_list=news_list, last_updated=datetime.utcnow(), lang=lang,
                               daily_links=daily_links,
                               path=urljoin(config.site + '/', path.rstrip('index.html')))
    with open(static_page, "w") as fp:
        fp.write(rendered)
    cost = (time.time() - start) * 1000
    logger.info(f'Written {len(rendered)} bytes to {static_page}, cost(ms): {cost:.2f}')


def get_daily_links():
    daily_dir = os.path.join(config.output_dir, 'daily')
    if not os.path.exists(daily_dir):
        return []
    links = []
    for name in os.listdir(daily_dir):
        if os.path.isdir(os.path.join(daily_dir, name)):
            try:
                datetime.strptime(name, '%Y-%m-%d')
                links.append(name)
            except ValueError:
                continue  # Ignore directories that are not in 'YYYY-MM-DD' format
    links.sort(reverse=True)
    return links



def gen_feed(news_list):
    start = time.time()
    feed = AtomFeed('Hacker News Summary',
                    updated=datetime.utcnow(),
                    feed_url=f'{config.site}/feed.xml',
                    url={config.site},
                    author={
                        'name': 'polyrabbit',
                        'uri': 'https://github.com/polyrabbit/'}
                    )
    for i, news in enumerate(news_list):
        if news.get_score() <= config.openai_score_threshold:
            # RSS readers doesnot update their content, so wait until we have a better summary, to provide a consistent view to users
            continue
        img_tag = ''
        if news.image:
            img_tag = f'<img src="{news.image.url}" style="{news.image.get_size_style(220)}" /><br />'
        feed.add(news.title,
                 content='%s%s%s%s' % (
                     img_tag,
                     # not None
                     truncate(news.summary) if news.summarized_by.can_truncate() else news.summary,
                     (
                             ' <a href="%s" target="_blank">[summary]</a>' % f'{config.site}/#{news.slug()}'),
                     (
                         ' <a href="%s" target="_blank">[comments]</a>' % news.comment_url if news.comment_url else '')),
                 author={
                     'name': news.author,
                     'uri': news.author_link
                 } if news.author_link else (),
                 url=news.url,
                 updated=news.submit_time, )
    rendered = feed.to_string()
    output_path = os.path.join(config.output_dir, "feed.xml")
    with open(output_path, "w") as fp:
        fp.write(rendered)
    cost = (time.time() - start) * 1000
    logger.info(f'Written {len(rendered)} bytes to {output_path}, cost(ms): {cost:.2f}')


if __name__ == '__main__':
    if args.page == 'daily':
        gen_daily()
    else:
        gen_frontpage()
        db.translation.expire()
        db.summary.expire()
        db.image.expire()
