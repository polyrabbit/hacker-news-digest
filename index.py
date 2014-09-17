import logging
from flask import Flask, abort
from flask import render_template

import sae.kvdb

app = Flask(__name__)
logger = logging.getLogger(__name__)
kv = sae.kvdb.KVClient()

from hackernews import HackerNews
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - [%(asctime)s] %(message)s')
hn = HackerNews()
hn.update()

@app.route("/hackernews")
@app.route('/')
def hackernews():
    return render_template('index.html', title='Hacker News',
            news_list=map(lambda i: i[1], kv.get_by_prefix('')))

@app.route("/startupnews")
def startupnews():
    return render_template('index.html', title='Startup News',
            news_list=map(lambda i: i[1], kv.get_by_prefix('')))


if __name__ == "__main__":
    app.run()
