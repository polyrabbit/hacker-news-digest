import json
import logging
import os

import config
from page_content_extractor import session

logger = logging.getLogger(__name__)

summary_cache = {}

if os.environ.get('DISABLE_SUMMARY_CACHE') != '1':
    try:
        resp = session.get(f'{config.site}/summary.json')
        resp.raise_for_status()
        summary_cache = resp.json()
    except Exception as e:
        logger.warning("Failed to load last summary cache, %s", e)
else:
    logger.warning("Summary cache is disabled by env DISABLE_SUMMARY_CACHE=1")


def get(url, model=None):
    if url in summary_cache:
        if model is None or summary_cache[url]['model'] == model.value:
            return summary_cache[url]['summary']
    return ''


def save(news_list):
    summaries = {n.url: {'summary': n.summary, 'model': n.summarized_by.value} for n in news_list}
    rendered = json.dumps(summaries, indent=2)
    output_path = os.path.join(config.output_dir, "summary.json")
    with open(output_path, "w") as fp:
        fp.write(rendered)
    logger.info(f'Written {len(rendered)} bytes to {output_path}')
