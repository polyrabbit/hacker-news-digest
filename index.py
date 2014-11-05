import logging

from urlparse import urlparse, urlunparse
from flask import (
    Flask, render_template, abort, request, send_from_directory, send_file,
    Response, redirect
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

@app.before_request
def redirect_naked_domain():
    """Redirect hackernews.im to www.hackernews.im, cuz heroku doesnot support a nacked host"""
    # How I miss nginx here
    if request.host.endswith('herokuapp.com'):
        urlparts = urlparse(request.url)
        urlparts_list = list(urlparts)
        urlparts_list[1] = 'www.hackernews.im'
        return redirect(urlunparse(urlparts_list), code=301)

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

@app.route('/update/<what>', methods=['POST'])
@app.route('/update', methods=['POST'])
def update(what=None):
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

@app.route('/favicon.ico')
@app.route('/sitemap.xml')
def static_files():
    return send_from_directory(app.static_folder, request.path[1:])

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=app.config['PORT'])

