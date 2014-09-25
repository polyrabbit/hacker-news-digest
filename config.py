import socket
import os
import logging

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - [%(asctime)s] %(message)s')

socket.setdefaulttimeout(20)

port = int(os.environ.get('PORT', 5000))

HN_UPDATE_KEY = os.environ.get('HN_UPDATE_KEY')

# Free account on heroku
DB_CONNECTION_LIMIT = 20
# Database
db_url = os.environ.get("DATABASE_URL",
    'postgres://postgres@localhost:5432/postgres')\
    .replace('postgres://', 'postgresql://')
db_pool_size = 5
db_max_overflow = 0

# Gunicorn
bind = "0.0.0.0:%s" % port
# workers = multiprocessing.cpu_count() *2 +1
workers = DB_CONNECTION_LIMIT / db_pool_size
# threads = db_pool_size
accesslog = '-'
errorlog = '-'

