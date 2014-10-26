import socket
import os
import logging

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - [%(asctime)s] %(message)s')
logging.getLogger("requests").setLevel(logging.WARNING)

socket.setdefaulttimeout(20)

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

# Gunicorn
bind = "0.0.0.0:%s" % PORT
# workers = multiprocessing.cpu_count() *2 +1
workers = 3
threads = SQLALCHEMY_POOL_SIZE
accesslog = '-'
errorlog = '-'

summary_length = 250
sites_for_users = ('github.com', 'medium.com')
