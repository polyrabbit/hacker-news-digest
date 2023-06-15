import json
import logging
import os

import config
from hacker_news.dict_cache import DictCache
from page_content_extractor import session

logger = logging.getLogger(__name__)
TTL = 5 * 24 * 60 * 60

cache = {
    'Hacker News Summary - by ChatGPT': DictCache(zh='Hacker News 摘要 - ChatGPT 强力驱动'),
    'Translate': DictCache(zh='翻译')
}

if not config.disable_translation_cache:
    try:
        resp = session.get(f'{config.site}/translation.json')
        resp.raise_for_status()
        cache = dict({k: DictCache(**v) for k, v in resp.json().items()}, **cache)
    except Exception as e:
        logger.warning("Failed to load translation cache, %s", e)
else:
    logger.warning("Translation cache is disabled by env DISABLE_TRANSLATION_CACHE=1")


# TODO: enable other translation api
def get(text, to_lang):
    if text in cache:
        if to_lang in cache[text] and cache[text][to_lang]:
            cache[text].mark_accessed()
            return cache[text][to_lang]
    return text


def add(source, target, lang):
    if source and target:
        cache[source] = DictCache({lang: target})
        cache[source].mark_accessed()


def save(output_dir=config.output_dir):
    valid_translation = {}
    for text in cache:
        if cache[text].expired(TTL):  # Let it crash if value is not CacheDict
            continue
        valid_translation[text] = cache[text]
    rendered = json.dumps(valid_translation)
    output_path = os.path.join(output_dir, "translation.json")
    with open(output_path, "w") as fp:
        fp.write(rendered)
    logger.info(f'Written {len(rendered)} bytes, {len(valid_translation)} items to {output_path}')
    return len(valid_translation)
