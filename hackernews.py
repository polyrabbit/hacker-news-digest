# coding: utf-8
import logging

from news_parser import HackerNewsParser
from page_content_extractor import legendary_parser_factory

logger = logging.getLogger(__name__)

from config import summary_length
import models


class HackerNews(HackerNewsParser):
    model_class = models.HackerNews

    def update(self, force=False):
        stats = {'updated': 0, 'added': 0, 'removed': 0, 'errors': []}
        if force:
            stats['removed'] += self.model_class.remove_except([])
        news_list = self.parse_news_list()
        # add new items
        for news in news_list:
            try:
                # Use news url as the key
                news_inst = self.model_class.query.get(news['url'])
                if news_inst:
                    if news_inst.summary:
                        logger.info('Updating %s', news['url'])
                        stats['updated'] += 1
                        # We need the url so we can't pop it here
                        _news = news.copy()
                        self.model_class.update(_news.pop('url'), **_news)
                        continue
                    # If we don't find the summary, something has gone wrong,
                    # just delete the whole and start over again.
                    self.model_class.delete(news['url'])
                    stats['removed'] += 1
                self.insert_news(news, stats)
            except Exception as e:
                logger.exception(e)
                stats['errors'].append(str(e))

        if not force:
            # clean up old items
            stats['removed'] += self.model_class.remove_except([n['url'] for n in news_list])
        return stats

    def insert_news(self, news, stats):
        try:
            logger.info("Fetching %s", news['url'])
            parser = legendary_parser_factory(news['url'])
            news['summary'] = parser.get_summary(summary_length)
            news['favicon'] = parser.get_favicon_url()
            tm = parser.get_illustration()
            if tm:
                img_id = models.Image.add(
                    url=tm.url,
                    content_type=tm.content_type,
                    raw_data=tm.raw_data)
                news['img_id'] = img_id
        except Exception as e:
            logger.exception('Failed to fetch %s, %s', news['url'], e)
            stats['errors'].append(str(e))
        finally:
            self.model_class.add(**news)
            stats['added'] += 1


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - [%(asctime)s] %(message)s')
    # unittest.main()
    hn = HackerNews()
    hn.update()
