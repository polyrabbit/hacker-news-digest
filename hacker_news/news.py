import logging
import os
import pathlib
import re
from enum import Enum
from hashlib import md5
from urllib.parse import urlparse

import openai
from jinja2 import filters, Environment

import config
from page_content_extractor import parser_factory, session

logger = logging.getLogger(__name__)
environment = Environment()
summary_cache = {}

try:
    resp = session.get(f'{config.site}/summary.json')
    resp.raise_for_status()
    summary_cache = resp.json()
except Exception as e:
    logger.warning("Failed to load last summary cache, %s", e)


class SummarizedBy(Enum):
    LOCAL = "Parser"
    OPENAI = "OpenAI"


class News:

    def __init__(self, rank=-1, title='', url='', comhead='', score='', author='',
                 author_link='', submit_time='', comment_cnt='', comment_url=''):
        self.rank = rank
        self.title = title
        self.url = url
        self.comhead = comhead
        self.score = score
        self.author = author
        self.author_link = author_link
        self.submit_time = submit_time
        self.comment_cnt = comment_cnt
        self.comment_url = comment_url
        self.summary = ''
        self.summarized_by = SummarizedBy.LOCAL
        self.favicon = ''
        self.image = None
        self.img_id = None

    def get_image_url(self):
        if self.image and self.image.url:
            return self.image.url
        return ''

    def pull_content(self):
        try:
            logger.info("#%d, fetching %s", self.rank, self.url)
            parser = parser_factory(self.url)
            self.favicon = parser.get_favicon_url()
            # Replace consecutive spaces with a single space
            self.content = re.sub(r'\s+', ' ', parser.get_content(config.max_content_size))
            self.summarize()
            tm = parser.get_illustration()
            if tm:
                fname = md5(tm.raw_data).hexdigest()
                fname += pathlib.Path(urlparse(tm.url).path).suffix
                tm.save(os.path.join(config.output_dir, "image", fname))
                self.image = tm
                self.img_id = fname
        except Exception as e:
            logger.exception('Failed to fetch %s, %s', self.url, e)

    def summarize(self):
        if not self.content:
            return
        if self.content.startswith('<iframe '):
            self.summary = self.content
        else:
            summary = self.summarize_by_openai(self.content.strip())
            self.summary = filters.do_truncate(environment, summary, length=config.summary_size,
                                               end=' ...')

    def summarize_by_openai(self, content):
        if self.url in summary_cache and summary_cache[self.url]['by'] == SummarizedBy.OPENAI.value:
            logger.info("Cache hit for %s", self.url)
            self.summarized_by = SummarizedBy.OPENAI
            return summary_cache[self.url]['summary']

        if not openai.api_key:
            logger.warning("OpenAI API key is not set")
            return content
        if len(content) <= config.summary_size:
            logger.info("No need to summarize since we have a small text")
            return content
        if self.get_score() <= 10:  # oh my precious quota
            logger.info("Score %d is too small, ignore openai", self.get_score())
            return content

        prompt = f'''Summarize following article, delimited by ```, in at most 60 words.
```{content}```'''
        try:
            resp = openai.ChatCompletion.create(model='gpt-3.5-turbo',
                                                messages=[
                                                    {'role': 'user', 'content': prompt},
                                                ],
                                                max_tokens=int(config.summary_size / 4),
                                                stream=False,
                                                temperature=0,
                                                n=1,  # only one choice
                                                timeout=30)
            logger.info(resp)
            content = resp['choices'][0]['message']['content'].strip()
            self.summarized_by = SummarizedBy.OPENAI
        except Exception as e:
            logger.warning('Failed to summarize using openai, %s', e)
        return content

    def get_score(self):
        try:
            return int(self.score.strip())
        except:
            return 0
