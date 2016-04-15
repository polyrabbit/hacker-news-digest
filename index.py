import logging
from time import time
from urlparse import urljoin
from datetime import datetime

from flask import (
    Flask, render_template, abort, request, send_file,
    Response, jsonify, url_for
)
from werkzeug.http import is_resource_modified
from werkzeug.contrib.atom import AtomFeed
from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_object('config')
db = SQLAlchemy(app)

from ago import human
# Avoid circular imports
# from models import HackerNews, StartupNews, Image
import models

logger = logging.getLogger(__name__)

@app.route("/hackernews")
@app.route('/')
def hackernews():
    dt = models.LastUpdated.get('hackernews')
    if dt and not is_resource_modified(request.environ, None, None, last_modified=dt):
        return Response(status=304)
    resp = Response(render_template(
                'hackernews.html',
                news_list=models.HackerNews.query.order_by('rank').all(),
                last_updated=dt))
    set_cache(resp, dt)
    return resp

@app.route("/startupnews")
def startupnews():
    dt = models.LastUpdated.get('startupnews')
    if dt and not is_resource_modified(request.environ, None, None, last_modified=dt):
        return Response(status=304)
    resp = Response(render_template(
                'startupnews.html',
                news_list=models.StartupNews.query.order_by('rank').all(),
                last_updated=dt))
    set_cache(resp, dt)
    return resp

@app.route('/img/<img_id>')
def image(img_id):
    if request.if_none_match or request.if_modified_since:
        return Response(status=304)
    img = models.Image.query.get_or_404(img_id)
    return send_file(img.makefile(), img.content_type, cache_timeout=864000, conditional=True)

@app.route('/update/hackernews', methods=['POST'], defaults={'site': 'hackernews'})
@app.route('/update/startupnews', methods=['POST'], defaults={'site': 'startupnews'})
@app.route('/update', methods=['POST'], defaults={'site': None})
def update(site):
    if request.form.get('key') != app.config['HN_UPDATE_KEY']:
        abort(401)
    # circular imports again
    from hackernews import HackerNews
    from startupnews import StartupNews
    force = 'force' in request.args
    stats = {}
    if site == 'hackernews' or site is None:
        stats['hackernews'] = HackerNews().update(force)
        models.LastUpdated.update('hackernews')
    if site == 'startupnews' or site is None:
        stats['startupnews'] = StartupNews().update(force)
        models.LastUpdated.update('startupnews')
    return jsonify(**stats)

@app.route('/startupnews/feed', defaults={'site': 'startupnews'})
@app.route('/feed', defaults={'site': 'hackernews'})
def feed(site):
    gte = request.args.get('gte', 0)
    try:
        gte = int(gte)
    except ValueError:
        gte = 0
    if site == 'hackernews':
        title = 'Hacker News Digest'
        news_list = models.HackerNews.query\
            .filter(models.HackerNews.score>=gte).order_by('submit_time desc').all()
    else:
        title = 'Startup News Digest'
        news_list = models.StartupNews.query\
            .filter(models.StartupNews.score>=gte).order_by('submit_time desc').all()

    feed = AtomFeed(title,
                    updated=models.LastUpdated.get(site),
                    feed_url=request.url,
                    url=urljoin(request.url_root, url_for(site)),
                    author={
                        'name': 'polyrabbit',
                        'uri': 'https://github.com/polyrabbit/'}
                    )
    for news in news_list:
        feed.add(news.title,
                 content=news.summary and 
                 ('<img src="%s" style="width: 220px; float: left" />' % news.image.url if news.img_id else '') 
                     + news.summary,
                 author={
                     'name': news.author,
                     'uri': news.author_link
                 } if news.author_link else (),
                 url=news.url,
                 updated=news.submit_time,)
    return feed.get_response()

@app.add_template_filter
def natural_datetime(dt, precisoin):
    # We use utc timezone because dt is in utc
    return human(datetime.utcnow()-dt, precisoin)

def set_cache(response, last_updated):
    delta = 0
    if last_updated:
        # Update every 10 minutes
        delta = 10*60 - int((datetime.utcnow() - last_updated).total_seconds())
        if delta < 0:
            delta = 0
    response.cache_control.public = True
    response.cache_control.max_age = delta
    response.expires = int(time() + delta)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=app.config['PORT'])

