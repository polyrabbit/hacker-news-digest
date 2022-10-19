from hackernews import HackerNews
import logging
from urllib.parse import urljoin

import models

logger = logging.getLogger(__name__)

class StartupNews(HackerNews):
    end_point = 'http://news.dbanotes.net/'
    model_class = models.StartupNews

    def get_comment_url(self, path):
        if path is None:
            return None
        return urljoin(self.end_point, path)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - [%(asctime)s] %(message)s')
    # unittest.main()
    sn = StartupNews()
    sn.update()

