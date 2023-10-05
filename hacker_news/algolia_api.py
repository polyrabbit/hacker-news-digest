# coding: utf-8
import calendar
import logging
from collections import defaultdict
from datetime import datetime, timedelta

import config
from db.summary import filter_url
from hacker_news.news import News
from hacker_news.parser import parse_site
from page_content_extractor import session

logger = logging.getLogger(__name__)

end_point = 'https://hn.algolia.com/api/v1/search_by_date?tags=story&hitsPerPage=1000&page=%d&numericFilters=%s'


def get_daily_news(updatable_within_days) -> dict[datetime, list[News]]:
    news_list = get_news(updatable_within_days)
    url_list = [n.url for n in news_list]
    url_set = filter_url(url_list)

    daily_items = defaultdict(list)
    for news in news_list:
        if news.url not in url_set:
            continue
        date = news.submit_time.date()
        daily_items[date].append(news)
    for date, items in daily_items.items():
        items.sort(key=lambda x: x.score, reverse=True)
        for i, item in enumerate(items):
            item.rank = i
    return daily_items


def get_news(updatable_within_days):
    end = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    items = []
    # algolia limits number of hits to 1000, regardless of page parameter, see https://github.com/algolia/hn-search/issues/230
    while updatable_within_days > 0:
        days_span = min(updatable_within_days, 3)
        start = end - timedelta(days=days_span)
        filter = f'points>{config.openai_score_threshold},created_at_i>={calendar.timegm(start.utctimetuple())},created_at_i<{calendar.timegm(end.utctimetuple())}'
        for hits in get_all_stories(filter):
            for rank, hit in enumerate(hits):
                comment_url = f'https://news.ycombinator.com/item?id={hit["objectID"]}'
                url = hit.get('url')
                if not url:
                    url = comment_url
                items.append(News(
                    rank=rank,
                    title=hit['title'],
                    url=url,
                    comhead=parse_site(url),
                    score=hit['points'],
                    author=hit['author'],
                    author_link=f'https://news.ycombinator.com/user?id={hit["author"]}',
                    submit_time=datetime.utcfromtimestamp(hit['created_at_i']),
                    comment_cnt=hit['num_comments'],
                    comment_url=comment_url
                ))
            end = start
            updatable_within_days -= days_span
    return items


# minimize number of algolia requests
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
        if page >= story_resp['nbPages']:
            break
        loop_limit -= 1
        if loop_limit <= 0:
            logger.warning(f'loop limit reached, current page {page}')
            break
