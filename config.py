import os
import logging

DEBUG = 'DEBUG' in os.environ

logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO,
                    format='%(levelname)s - [%(asctime)s] %(message)s')
logging.getLogger("requests").setLevel(logging.WARNING)

PORT = int(os.environ.get('PORT', 5000))

# Fail fast
HN_UPDATE_KEY = os.environ.get('HN_UPDATE_KEY')

# Free account on heroku
DB_CONNECTION_LIMIT = 20
# Database
try:
    SQLALCHEMY_DATABASE_URI = os.environ['VCAP_SERVICES']['postgresql-9.1'][0]['credentials']['uri']
except KeyError:
    # Easier to ask for forgiveness rather than permission
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", 'postgres://postgres@localhost:5432/hndigest')
SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://')
SQLALCHEMY_POOL_SIZE = 5
SQLALCHEMY_MAX_OVERFLOW = 5
SQLALCHEMY_ECHO = DEBUG

# Gunicorn
# As suggested by nginx-buildpack
bind = "unix:/tmp/nginx.socket"
# Each worker occupies 25M memory
# workers = multiprocessing.cpu_count()*2
workers = 3
max_requests = 100
threads = SQLALCHEMY_POOL_SIZE
accesslog = '-'
errorlog = '-'

summary_length = 250
sites_for_users = ('github.com', 'medium.com')

