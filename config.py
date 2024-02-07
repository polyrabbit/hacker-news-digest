import logging
import os
import random
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
    syslog.setLevel(logging.WARNING)  # avoid insufficient quota
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
summary_ttl = int_env('SUMMARY_TTL_DAYS', 60) * 24 * 60 * 60
updatable_within_days = int_env('UPDATABLE_WITHIN_DAYS', 3)
assert updatable_within_days < summary_ttl / (24 * 60 * 60)

sites_for_users = ('github.com', 'medium.com', 'twitter.com')

disable_ads = os.getenv('DISABLE_ADS') == '1'
disable_summary_cache = os.getenv('DISABLE_SUMMARY_CACHE') == '1'
disable_translation_cache = os.getenv('DISABLE_TRANSLATION_CACHE') == '1'
force_fetch_feature_image = os.getenv('FORCE_FETCH_FEATURE_IMAGE') == '1'

disable_llama = os.getenv('DISABLE_LLAMA') == '1'
llama_model = os.getenv('LLAMA_MODEL_PATH') or os.path.expanduser('~/.cache/huggingface/hub/models_llama-2-7b-chat.Q6_K.gguf')
logger.info(f'Use llama model {llama_model}')

disable_transformer = os.getenv('DISABLE_TRANSFORMER') == '1'
transformer_model = os.getenv('TRANSFORMER_MODEL') or 't5-large'
logger.info(f'Use transformer model {transformer_model}')


def coze_enabled():
    return coze_api_endpoint and coze_api_key and coze_bot_id


coze_api_endpoint = os.getenv('COZE_API_ENDPOINT')
coze_api_key = os.getenv('COZE_API_KEY')
coze_bot_id = os.getenv('COZE_BOT_ID')
logger.info(f'Coze api {"enabled" if coze_enabled() else "disabled"}')

openai_keys = os.getenv('OPENAI_API_KEY').split(',') if os.getenv('OPENAI_API_KEY') else [None]
openai.api_key = random.choice(openai_keys)  # Round-robin available keys
openai_key_index = openai_keys.index(openai.api_key)
logger.info(f'Use openai api key #{openai_key_index}')
openai_model = os.getenv('OPENAI_MODEL') or 'gpt-3.5-turbo'
openai_score_threshold = int_env('OPENAI_SCORE_THRESHOLD', 20)
local_llm_score_threshold = 10
logger.info(f'Use openai model {openai_model}')

output_dir = os.path.join(os.path.dirname(__file__), 'output/')
image_dir = os.path.join(output_dir, 'image/')
