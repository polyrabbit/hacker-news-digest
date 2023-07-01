import logging
import os
from logging.handlers import SysLogHandler
from urllib.parse import urlparse

import openai
from dotenv import load_dotenv

load_dotenv()

DEBUG = os.getenv('DEBUG') == '1'

site = 'https://hackernews.betacat.io'

log_handlers = [logging.StreamHandler()]
if os.getenv('SYSLOG_ADDRESS'):
    parsed = urlparse("//" + os.getenv('SYSLOG_ADDRESS'))
    syslog = SysLogHandler(address=(parsed.hostname, parsed.port))
    log_handlers.append(syslog)

logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO,
                    format='%(asctime)s %(levelname)s [%(filename)s:%(lineno)d %(funcName)s] - %(message)s',
                    handlers=log_handlers)
logger = logging.getLogger()


def int_env(name, default):
    try:
        return int(os.environ[name])
    except:
        return default


PORT = int_env('VCAP_APP_PORT', 5000)

# Database
DATABASE_URL = os.environ.get('DATABASE_URL',
                              f'sqlite:///{os.path.dirname(__file__)}/hackernews.db')
DATABASE_ECHO_SQL = os.getenv('DATABASE_ECHO_SQL') == '1'
SLOW_SQL_MS = int_env('SLOW_SQL_MS', 1000)

max_content_size = 64 << 10  # cost 2.5 min when parsing large pdf
summary_size = 400
summary_ttl = int_env('SUMMARY_TTL_HOUR', 30 * 24) * 60 * 60
sites_for_users = ('github.com', 'medium.com', 'twitter.com')

disable_ads = os.getenv('DISABLE_ADS') == '1'
disable_summary_cache = os.getenv('DISABLE_SUMMARY_CACHE') == '1'
disable_translation_cache = os.getenv('DISABLE_TRANSLATION_CACHE') == '1'

disable_transformer = os.getenv('DISABLE_TRANSFORMER') == '1'
transformer_model = os.getenv('TRANSFORMER_MODEL') or 't5-large'
logger.info(f'Use transformer model {transformer_model}')

openai.api_key = os.getenv("OPENAI_API_KEY")
openai_model = os.getenv('OPENAI_MODEL') or 'gpt-3.5-turbo'
openai_score_threshold = int_env('OPENAI_SCORE_THRESHOLD', 20)
logger.info(f'Use openai model {openai_model}')

output_dir = os.path.join(os.path.dirname(__file__), 'output/')
