import os
import logging
from subprocess import Popen

from flask import (
    Flask, render_template, abort, request, send_from_directory, send_file
)

from db import ImageStorage, HnStorage, SnStorage
from hackernews import HackerNews
from startupnews import StartupNews

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - [%(asctime)s] %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

imstore = ImageStorage()
hn = HackerNews()
sn = StartupNews()

@app.route("/hackernews")
@app.route('/')
def hackernews():
    return render_template('index.html', title='Hacker News',
            news_list=hn.get_all())

@app.route("/startupnews")
def startupnews():
    return render_template('index.html', title='Startup News',
            news_list=sn.get_all())

@app.route('/img/<img_id>')
def image(img_id):
    img = imstore.get(img_id)
    if not img:
       abort(404)
    from cStringIO import StringIO
    return send_file(StringIO(str(img.raw_data)), img.content_type)
    return str(img['raw_data']), 200, {'Content-Type': img['content_type']}

@app.route('/update/<what>', methods=['POST'])
@app.route('/update', methods=['POST'])
def update(what=None):
    if request.form.get('key') != os.environ.get('HN_UPDATE_KEY'):
        abort(401)
    if what == 'hackernews' or what is None:
        hn.update()
    if what == 'startupnews' or what is None:
        sn.update()
    return 'Great success!'

@app.route('/favicon.ico')
def static_files():
    return send_from_directory(app.static_folder, request.path[1:])

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

