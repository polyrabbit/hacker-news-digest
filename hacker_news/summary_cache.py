import json
import logging
import os
from enum import Enum

import config
from hacker_news.dict_cache import DictCache
from page_content_extractor import session

logger = logging.getLogger(__name__)
TTL = 1 * 24 * 60 * 60
EXPENSIVE_TTL = 5 * 24 * 60 * 60

cache = {}

if not config.disable_summary_cache:
    try:
        resp = session.get(f'{config.site}/summary.json')
        resp.raise_for_status()
        cache = {k: DictCache(**v) for k, v in resp.json().items()}
    except Exception as e:
        logger.warning("Failed to load last summary cache, %s", e)
else:
    logger.warning("Summary cache is disabled by env DISABLE_SUMMARY_CACHE=1")


class Model(Enum):
    PREFIX = 'Prefix'
    FULL = 'Full'
    EMBED = 'Embed'
    OPENAI = 'OpenAI'
    TRANSFORMER = 'GoogleT5'

    def can_truncate(self):
        return self not in (Model.OPENAI, Model.EMBED)


def get(url, model=None):
    if config.disable_summary_cache:
        return ''
    if url in cache:
        if model is None or cache[url]['model'] == model.value:
            cache[url].mark_accessed()
            return cache[url]['summary']
    return ''


def add(url, summary, model):
    if summary:
        cache[url] = DictCache(summary=summary, model=model.value)
        cache[url].mark_accessed()


def save(output_dir=config.output_dir):
    valid_summary = {}
    for url in cache:
        ttl = TTL
        if cache[url]['model'] in (Model.OPENAI.value, Model.TRANSFORMER.value):
            ttl = EXPENSIVE_TTL
        if cache[url].expired(ttl):
            continue
        valid_summary[url] = cache[url]
    rendered = json.dumps(valid_summary)
    output_path = os.path.join(output_dir, "summary.json")
    with open(output_path, "w") as fp:
        fp.write(rendered)
    logger.info(f'Written {len(rendered)} bytes, {len(valid_summary)} items to {output_path}')
    return len(valid_summary)
