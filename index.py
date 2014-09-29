import logging

from flask import (
    Flask, render_template, abort, request, send_from_directory, send_file,
    Response
)

import config
from db import ImageStorage
from hackernews import HackerNews
from startupnews import StartupNews

logger = logging.getLogger(__name__)

app = Flask(__name__)

# @app.before_request
# def before_request():
#     print '+'*10, request.path
#
@app.route("/hackernews")
@app.route('/')
def hackernews():
    hn = HackerNews()
    return render_template('index.html', title='Hacker News',
            news_list=hn.get_all(), navs=[
        ('New', 'https://news.ycombinator.com/newest'),
        ('Comments', 'https://news.ycombinator.com/newcomments'),
        ('Show', 'https://news.ycombinator.com/show'),
        ('Ask', 'https://news.ycombinator.com/ask'),
        ('Jobs', 'https://news.ycombinator.com/jobs'),
        ('Submit', 'https://news.ycombinator.com/submit')]
    )

@app.route("/startupnews")
def startupnews():
    sn = StartupNews()
    return render_template('index.html', title='Startup News',
            news_list=sn.get_all(), navs=[
            ('New', 'http://news.dbanotes.net/newest'),
            ('Comments', 'http://news.dbanotes.net/newcomments'),
            ('Leaders', 'http://news.dbanotes.net/leaders'),
            ('Submit', 'http://news.dbanotes.net/submit')
        ])

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
    if what == 'hackernews' or what is None:
        HackerNews().update()
    if what == 'startupnews' or what is None:
        StartupNews().update()
    return 'Great success!'

@app.route('/sitemap.xml')
def static_files():
    return send_from_directory(app.static_folder, request.path[1:])

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=config.port)

