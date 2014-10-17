import logging
import re
from datetime import datetime

from flask import (
    Flask, render_template, abort, request, send_from_directory, send_file,
    Response
)
from ago import human

import config
from page_content_extractor.utils import word_count
from db import ImageStorage
from hackernews import HackerNews
from startupnews import StartupNews

logger = logging.getLogger(__name__)

app = Flask(__name__)
# [0] for hackernews, [1] for startupnews
last_synced = [None, None]

# @app.before_request
# def before_request():
#     print last_synced

@app.route("/hackernews")
@app.route('/')
def hackernews():
    hn = HackerNews()
    news = hn.get_all()
    for n in news:
        n.submit_time = human(datetime.fromtimestamp(float(n.submit_time)), 1)
    return render_template('index.html',
            title='Hacker News',
            news_list=news,
            navs=[
                ('Hacker News', 'https://news.ycombinator.com/news'),
                ('New', 'https://news.ycombinator.com/newest'),
                ('Comments', 'https://news.ycombinator.com/newcomments'),
                ('Show', 'https://news.ycombinator.com/show'),
                ('Ask', 'https://news.ycombinator.com/ask'),
                ('Jobs', 'https://news.ycombinator.com/jobs'),
                ('Submit', 'https://news.ycombinator.com/submit')],
            last_synced = last_synced[0] and human(last_synced[0], 1)
        )

@app.route("/startupnews")
def startupnews():
    sn = StartupNews()
    return render_template('index.html',
            title='Startup News',
            news_list=sn.get_all(),
            navs=[
                ('Startup News', 'http://news.dbanotes.net/news'),
                ('New', 'http://news.dbanotes.net/newest'),
                ('Comments', 'http://news.dbanotes.net/newcomments'),
                ('Leaders', 'http://news.dbanotes.net/leaders'),
                ('Submit', 'http://news.dbanotes.net/submit')],
            last_synced = last_synced[1] and human(last_synced[1], 1)
        )

@app.route('/img/<int:img_id>')
def image(img_id):
    if request.if_none_match or request.if_modified_since:
        return Response(status=304)
    imstore = ImageStorage()
    img = imstore.get(img_id)
    if not img:
        abort(404)
    return send_file(img.makefile(), img.content_type, conditional=True)

@app.route('/update/<what>', methods=['POST'])
@app.route('/update', methods=['POST'])
def update(what=None):
    if request.form.get('key') != config.HN_UPDATE_KEY:
        abort(401)
    force = 'force' in request.args
    if what == 'hackernews' or what is None:
        HackerNews().update(force)
        last_synced[0] = datetime.now()
    if what == 'startupnews' or what is None:
        StartupNews().update(force)
        last_synced[1] = datetime.now()
    return 'Great success!'

@app.route('/sitemap.xml')
def static_files():
    return send_from_directory(app.static_folder, request.path[1:])

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=config.port)

