import json
import logging
import os

import openai
from dotenv import load_dotenv

load_dotenv()

DEBUG = 'DEBUG' in os.environ

site = 'https://hackernews.betacat.io'

logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO,
                    format='%(asctime)s %(levelname)s [%(filename)s:%(lineno)d %(funcName)s] - %(message)s')
logger = logging.getLogger(__name__)

try:
    PORT = int(os.environ['VCAP_APP_PORT'])
except KeyError:
    # Easier to ask for forgiveness rather than permission
    PORT = int(os.environ.get('PORT', 5000))

# Database
try:
    vcap_services = os.environ['VCAP_SERVICES']
    SQLALCHEMY_DATABASE_URI = json.loads(vcap_services)['postgresql-9.1'][0]['credentials']['uri']
except Exception:
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL",
                                             'postgres://postgres@localhost:5432/hndigest')
SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://')
SQLALCHEMY_POOL_SIZE = 5
SQLALCHEMY_MAX_OVERFLOW = 5
SQLALCHEMY_ECHO = DEBUG

max_content_size = 1 << 20
summary_size = 400
sites_for_users = ('github.com', 'medium.com', 'twitter.com')

disable_ads = os.getenv('DISABLE_ADS') == '1'
disable_summary_cache = os.getenv('DISABLE_SUMMARY_CACHE') == '1'

disable_transformer = os.getenv('DISABLE_TRANSFORMER') == '1'
transformer_model = os.getenv('TRANSFORMER_MODEL') or 't5-large'
logger.info(f'Use transformer model {transformer_model}')

openai.api_key = os.getenv("OPENAI_API_KEY")
openai_model = os.getenv('OPENAI_MODEL') or 'gpt-3.5-turbo'
openai_score_threshold = 20
try:
    openai_score_threshold = int(os.getenv('OPENAI_SCORE_THRESHOLD'))
except:
    pass
logger.info(f'Use openai model {openai_model}')

output_dir = os.path.join(os.path.dirname(__file__), "output/")
