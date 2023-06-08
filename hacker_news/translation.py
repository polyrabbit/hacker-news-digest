import json
import logging
import os

import config
from page_content_extractor import session

logger = logging.getLogger(__name__)

translation_cache = {
    'Hacker News Summary - by ChatGPT': {'zh': 'Hacker News 摘要 - ChatGPT 强力驱动'},
    'Translate': {'zh': '翻译'}
}

if not config.disable_translation_cache:
    try:
        resp = session.get(f'{config.site}/translation.json')
        resp.raise_for_status()
        translation_cache = resp.json()
    except Exception as e:
        logger.warning("Failed to load translation cache, %s", e)
else:
    logger.warning("Translation cache is disabled by env DISABLE_TRANSLATION_CACHE=1")

touched = []


# TODO: enable other translation api
def get(text, to_lang):
    if text in translation_cache:
        if to_lang in translation_cache[text]:
            touched.append(text)
            return translation_cache[text][to_lang]
    return text


def add(source, target, lang):
    translation_cache[source] = {lang: target}


def save():
    fresh_translation = {}
    for text in touched:
        fresh_translation[text] = translation_cache[text]
    rendered = json.dumps(fresh_translation, indent=2)
    output_path = os.path.join(config.output_dir, "translation.json")
    with open(output_path, "w") as fp:
        fp.write(rendered)
    logger.info(f'Written {len(rendered)} bytes to {output_path}')
    touched.clear()
