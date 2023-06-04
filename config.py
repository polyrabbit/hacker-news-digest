import json
import logging
import os

DEBUG = 'DEBUG' in os.environ

site = 'https://hackernews.betacat.io'

logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO,
                    format='%(asctime)s %(levelname)s [%(filename)s:%(lineno)d %(funcName)s] - %(message)s')

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

output_dir = os.path.join(os.path.dirname(__file__), "output/")
