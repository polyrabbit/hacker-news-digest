import logging
import os
from datetime import datetime

from ago import human
from feedwerk.atom import AtomFeed
from jinja2 import Environment, FileSystemLoader

import config
from hacker_news import summary_cache
from hacker_news.parser import HackerNewsParser

logger = logging.getLogger(__name__)


def natural_datetime(dt, precision):
    # We use utc timezone because dt is in utc
    return human(datetime.utcnow() - dt, precision)


def elapsed(dt):
    return (datetime.utcnow() - dt).total_seconds() * 1000


environment = Environment(
    loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates/")), autoescape=True)
environment.filters["natural_datetime"] = natural_datetime
environment.filters["elapsed"] = elapsed
environment.globals["disable_ads"] = config.disable_ads


# Generate github pages
def gen_page(news_list):
    template = environment.get_template("hackernews.html")
    static_page = os.path.join(config.output_dir, "index.html")
    rendered = template.render(news_list=news_list, last_updated=datetime.utcnow())
    with open(static_page, "w") as fp:
        fp.write(rendered)
    logger.info(f'Written {len(rendered)} bytes to {static_page}')


def gen_feed(news_list):
    feed = AtomFeed('Hacker News Digest',
                    updated=datetime.utcnow(),
                    feed_url=f'{config.site}/feed.xml',
                    url={config.site},
                    author={
                        'name': 'polyrabbit',
                        'uri': 'https://github.com/polyrabbit/'}
                    )
    for i, news in enumerate(news_list):
        img_tag = ''
        if news.image:
            img_tag = f'<img src="{news.image.url}" style="{news.image.get_size_style(220)} float: left" />'
        feed.add(news.title,
                 content='%s%s%s' % (
                     img_tag,
                     # not None
                     news.summary, (
                         ' <a href="%s" target="_blank">[comments]</a>' % news.comment_url if news.comment_url and news.comment_url else '')),
                 author={
                     'name': news.author,
                     'uri': news.author_link
                 } if news.author_link else (),
                 url=news.url,
                 updated=news.submit_time, )
        if i == 1 or i == 27:
            feed.add('placeholder',
                     content='''<article class="post-item" data-rank="{{ loop.index0 }}">
                            <ins class="adsbygoogle"
                                 style="display:block"
                                 data-ad-format="fluid"
                                 data-ad-layout-key="-et-7-f-rh+149"
                                 data-ad-client="ca-pub-9393129008813908"
                                 data-ad-slot="4020487288"></ins>
                            <script>
                                (adsbygoogle = window.adsbygoogle || []).push({});
                            </script>
                        </article>''',
                     url=f'{config.site}/?item={i}',
                     updated=datetime.utcnow())
    rendered = feed.to_string()
    output_path = os.path.join(config.output_dir, "feed.xml")
    with open(output_path, "w") as fp:
        fp.write(rendered)
    logger.info(f'Written {len(rendered)} bytes to {output_path}')


if __name__ == '__main__':
    hn = HackerNewsParser()
    news_list = hn.parse_news_list()
    for news in news_list:
        news.pull_content()
    summary_cache.save(news_list)
    gen_page(news_list)
    gen_feed(news_list)
