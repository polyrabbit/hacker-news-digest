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
SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL",
    'postgres://postgres@localhost:5432/postgres')\
    .replace('postgres://', 'postgresql://')
SQLALCHEMY_POOL_SIZE = 5
SQLALCHEMY_MAX_OVERFLOW = 5
SQLALCHEMY_ECHO = DEBUG

# Gunicorn
# As suggested by nginx-buildpack
bind = "unix:/tmp/nginx.socket"
workers = 3
threads = SQLALCHEMY_POOL_SIZE
accesslog = '-'
errorlog = '-'

summary_length = 250
sites_for_users = ('github.com', 'medium.com')

