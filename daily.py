import logging

from hacker_news.algolia_api import get_news

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    news_list = get_news()
    for news in news_list:
        news.pull_content()
