# coding: utf-8
import logging
from datetime import datetime, timedelta

import config
from hacker_news.news import News
from hacker_news.parser import parse_site
from page_content_extractor import session

logger = logging.getLogger(__name__)

end_point = 'https://hn.algolia.com/api/v1/search_by_date?tags=story&hitsPerPage=1000&page=%d&numericFilters=%s'


def get_news():
    today_midnight = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    updatable_date = today_midnight - timedelta(days=config.updatable_within_days)
    filter = f'points>={config.openai_score_threshold},created_at_i>={int(updatable_date.timestamp())},created_at_i<{int(today_midnight.timestamp())}'
    for hits in get_all_stories(filter):
        for rank, hit in enumerate(hits):
            comment_url = f'https://news.ycombinator.com/item?id={hit["objectID"]}'
            url = hit['url']
            if not url:
                url = comment_url
            yield News(
                rank=rank,
                title=hit['title'],
                url=url,
                comhead=parse_site(url),
                score=hit['points'],
                author=hit['author'],
                author_link=f'https://news.ycombinator.com/user?id={hit["author"]}',
                submit_time=datetime.fromtimestamp(hit['created_at_i']),
                comment_cnt=hit['num_comments'],
                comment_url=comment_url
            )


def get_all_stories(filter: str):
    page = 0
    loop_limit = 10
    while True:
        url = end_point % (page, filter)
        logger.info(f'fetching {url}')
        resp = session.get(url)
        resp.raise_for_status()
        story_resp = resp.json()
        hits = story_resp['hits']
        if not hits:
            break
        yield hits
        page = story_resp['page'] + 1
        loop_limit -= 1
        if not loop_limit:
            logger.warning(f'loop limit reached, current page {page}')
            break
