import logging

from flask import (
    Flask, render_template, abort, request, send_file,
    Response
)
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
    ts = models.LastUpdated.get('hackernews')
    return render_template('index.html',
            title='Hacker News Digest',
            news_list=models.HackerNews.query.all(),
            navs=[
                ('Hacker News', 'https://news.ycombinator.com/news'),
                ('New', 'https://news.ycombinator.com/newest'),
                ('Comments', 'https://news.ycombinator.com/newcomments'),
                ('Show', 'https://news.ycombinator.com/show'),
                ('Ask', 'https://news.ycombinator.com/ask'),
                ('Jobs', 'https://news.ycombinator.com/jobs'),
                ('Submit', 'https://news.ycombinator.com/submit')],
            last_updated = ts and human(ts, 1)
        )

@app.route("/startupnews")
def startupnews():
    ts = models.LastUpdated.get('startupnews')
    return render_template('index.html',
            title='Startup News Digest',
            news_list=models.StartupNews.query.all(),
            navs=[
                ('Startup News', 'http://news.dbanotes.net/news'),
                ('New', 'http://news.dbanotes.net/newest'),
                ('Comments', 'http://news.dbanotes.net/newcomments'),
                ('Leaders', 'http://news.dbanotes.net/leaders'),
                ('Submit', 'http://news.dbanotes.net/submit')],
            last_updated = ts and human(ts, 1)
        )

@app.route('/img/<int:img_id>')
def image(img_id):
    if request.if_none_match or request.if_modified_since:
        return Response(status=304)
    img = models.Image.query.get_or_404(img_id)
    return send_file(img.makefile(), img.content_type, conditional=True)

@app.route('/update/hackernews', methods=['POST'], defaults={'what': 'hackernews'})
@app.route('/update/startupnews', methods=['POST'], defaults={'what': 'startupnews'})
@app.route('/update', methods=['POST'], defaults={'what': None})
def update(what):
    if request.form.get('key') != app.config['HN_UPDATE_KEY']:
        abort(401)
    # circular imports again
    from hackernews import HackerNews
    from startupnews import StartupNews
    force = 'force' in request.args
    if what == 'hackernews' or what is None:
        HackerNews().update(force)
        models.LastUpdated.update('hackernews')
    if what == 'startupnews' or what is None:
        StartupNews().update(force)
        models.LastUpdated.update('startupnews')
    return 'Great success!'

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=app.config['PORT'])

