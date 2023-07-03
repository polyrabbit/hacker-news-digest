import logging
import os
from datetime import datetime
from urllib.parse import urljoin

from feedwerk.atom import AtomFeed
from jinja2 import Environment, FileSystemLoader, filters

import config
import db.translation
from db import image
from hacker_news.parser import HackerNewsParser

logger = logging.getLogger(__name__)


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


# Generate github pages
def gen_page(news_list):
    template = environment.get_template("hackernews.html")
    lang_output = {'en': {'fname':'index.html', 'path':'/'}, 'zh': {'fname':'zh.html', 'path':'/zh.html'}}
    for lang, output in lang_output.items():
        static_page = os.path.join(config.output_dir, output['fname'])
        rendered = template.render(news_list=news_list, last_updated=datetime.utcnow(), lang=lang, path=urljoin(config.site, output['path']))
        with open(static_page, "w") as fp:
            fp.write(rendered)
        logger.info(f'Written {len(rendered)} bytes to {static_page}')


def gen_feed(news_list):
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
                         ' <a href="%s" target="_blank">[comments]</a>' % news.comment_url if news.comment_url and news.comment_url else '')),
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
    logger.info(f'Written {len(rendered)} bytes to {output_path}')


if __name__ == '__main__':
    hn = HackerNewsParser()
    news_list = hn.parse_news_list()
    for news in news_list:
        news.pull_content()
    gen_page(news_list)
    gen_feed(news_list)
    db.translation.expire()
    db.summary.expire()
    db.image.expire()
