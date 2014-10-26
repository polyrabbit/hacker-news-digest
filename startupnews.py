from hackernews import HackerNews
import logging
import models

logger = logging.getLogger(__name__)

class StartupNews(HackerNews):
    end_point = 'http://news.dbanotes.net/'
    model_class = models.StartupNews

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - [%(asctime)s] %(message)s')
    # unittest.main()
    sn = StartupNews()
    sn.update()

