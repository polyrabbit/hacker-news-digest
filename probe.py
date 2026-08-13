# coding: utf-8
import argparse
import logging
import re
from datetime import datetime, timedelta

from db.summary import Model
from page_content_extractor.http import session

parser = argparse.ArgumentParser(description='Probe betacat.io sites')
parser.add_argument("site", choices=['hn', 'hn-zh', 'blog'], help="Specify site to probe")
logger = logging.getLogger(__name__)


def probe_hn_summary():
    url = 'https://hackernews.betacat.io/'
    resp = session.get(url)
    resp.raise_for_status()
    body = resp.text

    assert "Hacker News" in body, '"Hacker News" not in response'
    final_models = tuple(model for model in Model if model.is_final())
    final_model_names = ', '.join(model.value for model in final_models)
    final_summaries = sum(body.count(model.value) for model in final_models)
    assert final_summaries > 5, (
        f"Too few final summaries, only got {final_summaries}, counted models: {final_model_names}"
    )
    logger.info(f'Final summaries {final_summaries} times')

    pattern = r'Last updated: <span>(.*?)<\/span>'
    matches = re.search(pattern, body)

    time_updated_str = matches.group(1)
    time_updated = datetime.strptime(time_updated_str, "%Y-%m-%d %H:%M:%S %Z")

    current_time = datetime.utcnow()

    assert current_time <= time_updated + timedelta(hours=3), "Haven't been updated for three hours, last update: " + time_updated_str


def probe_hn_zh():
    url = 'https://hackernews.betacat.io/zh.html'
    resp = session.get(url)
    resp.raise_for_status()
    body = resp.text

    assert '摘要' in body


def probe_blog():
    url = 'https://blog.betacat.io/'
    resp = session.get(url)
    resp.raise_for_status()
    body = resp.text

    assert '喵叔没话说' in body


def main():
    args = parser.parse_args()
    if args.site == 'blog':
        probe_blog()
    elif args.site == 'hn-zh':
        probe_hn_zh()
    elif args.site == 'hn':
        probe_hn_summary()
    else:
        assert False


if __name__ == '__main__':
    main()
