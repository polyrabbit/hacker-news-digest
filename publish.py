import argparse
import logging
import os
import shutil
import time
from datetime import datetime, timedelta
from urllib.parse import urljoin

from feedwerk.atom import AtomFeed
from jinja2 import Environment, FileSystemLoader, filters
from markupsafe import Markup

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


PAGES = {'en': 'index.html', 'zh': 'zh.html'}


def page_url(directory, lang):
    # Pretty URL served by Pages: daily/x/index.html -> daily/x/, daily/x/zh.html -> daily/x/zh
    return urljoin(config.site + '/', directory + PAGES[lang].removesuffix('.html').removesuffix('index'))


def story_url(news, lang):
    # The archive is a story's permanent home, 404.html covers the day before it is generated
    return f"{page_url(f'daily/{news.submit_time:%Y-%m-%d}/', lang)}#{news.slug()}"


environment = Environment(
    loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates/")), autoescape=True)
environment.filters["translate"] = translate
environment.filters["truncate"] = truncate
environment.globals["config"] = config
environment.globals["page_url"] = page_url
environment.globals["story_url"] = story_url


def gen_frontpage():
    hn = HackerNewsParser()
    news_list = hn.parse_news_list()
    for news in news_list:
        news.pull_content()
    for news in news_list:  # In a separate pass, so llama.cpp keeps reusing the cached translation prompt
        news.translate()
    gen_page(news_list)
    gen_feed(news_list)
    gen_sitemap()


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
        # Not translated here, as they have been translated when showing on the front page
        gen_page(items, f'daily/{date.strftime("%Y-%m-%d")}/', date=date)
    oldest = (datetime.utcnow() - timedelta(days=config.archive_ttl_days)).strftime('%Y-%m-%d')
    for link in get_daily_links():
        if link < oldest:
            logger.info(f'Removing archive {link} older than {config.archive_ttl_days} days')
            shutil.rmtree(os.path.join(config.output_dir, 'daily', link))
    if links := get_daily_links():
        # Add a stable entry to the latest archive for the app shortcut
        with open(os.path.join(config.output_dir, 'daily', 'index.html'), 'w') as fp:
            fp.write(f'<meta http-equiv="refresh" content="0; url={links[0]}/">')


# Generate GitHub pages
def gen_page(news_list, directory='', date=None):
    if not news_list:
        return  # no overwrite
    template = environment.get_template('hackernews.html')
    os.makedirs(os.path.join(config.output_dir, directory), exist_ok=True)
    for lang, page in PAGES.items():
        start = time.time()
        static_page = os.path.join(config.output_dir, directory, page)
        rendered = template.render(news_list=news_list, last_updated=datetime.utcnow(), lang=lang,
                                   daily_links=get_daily_links(lang), date=date, directory=directory)
        with open(static_page, "w") as fp:
            fp.write(rendered)
        cost = (time.time() - start) * 1000
        logger.info(f'Written {len(rendered)} bytes to {static_page}, cost(ms): {cost:.2f}')


def get_daily_links(lang='en'):
    """Dates having a daily page in lang, older ones were generated before Chinese pages existed."""
    daily_dir = os.path.join(config.output_dir, 'daily')
    if not os.path.exists(daily_dir):
        return []
    links = []
    for name in os.listdir(daily_dir):
        if os.path.isfile(os.path.join(daily_dir, name, PAGES[lang])):
            try:
                datetime.strptime(name, '%Y-%m-%d')
                links.append(name)
            except ValueError:
                continue  # Ignore directories that are not in 'YYYY-MM-DD' format
    links.sort(reverse=True)
    return links


def gen_sitemap():
    urls = [page_url('', lang) for lang in PAGES]
    urls += [page_url(f'daily/{link}/', lang) for lang in PAGES for link in get_daily_links(lang)]
    with open(os.path.join(config.output_dir, 'sitemap.xml'), 'w') as fp:
        fp.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                 '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        fp.writelines(f'<url><loc>{url}</loc></url>\n' for url in urls)
        fp.write('</urlset>\n')
    logger.info(f'Written {len(urls)} urls to sitemap.xml')


def gen_feed(news_list):
    start = time.time()
    feed = AtomFeed('Hacker News Summary',
                    updated=datetime.utcnow(),
                    feed_url=f'{config.site}/feed.xml',
                    url=config.site,
                    author={
                        'name': 'polyrabbit',
                        'uri': 'https://github.com/polyrabbit/'}
                    )
    for news in news_list:
        if news.get_score() <= config.openai_score_threshold:
            # RSS readers doesnot update their content, so wait until we have a better summary, to provide a consistent view to users
            continue
        summary = truncate(news.summary) if news.summarized_by.can_truncate() else news.summary
        if not news.summarized_by.need_escape():
            summary = Markup(summary)  # Quoted page HTML, trusted as on the web page
        content = Markup('{} <a href="{}">[summary]</a>').format(summary, story_url(news, 'en'))
        if news.image:
            content = Markup('<img src="{}" {}><br>').format(news.image.url, Markup(news.image.get_size_attrs(220))) + content
        if news.comment_url:
            content += Markup(' <a href="{}">[comments]</a>').format(news.comment_url)
        feed.add(news.title,
                 content=str(content),  # A plain string, for Markup would skip XML escaping
                 author={
                     'name': news.author,
                     'uri': news.author_link
                 } if news.author_link else (),
                 url=news.url,
                 updated=news.submit_time)
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
