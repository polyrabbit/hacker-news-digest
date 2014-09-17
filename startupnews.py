from hackernews import HackerNews
import logging
from db import SnStorage

logger = logging.getLogger(__name__)

class StartupNews(HackerNews):
    end_point = 'http://news.dbanotes.net/'
    storage = SnStorage()

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - [%(asctime)s] %(message)s')
    # unittest.main()
    sn = StartupNews()
    sn.update()

