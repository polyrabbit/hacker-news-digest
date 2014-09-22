import os
import logging
from subprocess import Popen

from flask import (
    Flask, render_template, abort, request, send_from_directory
)

from db import ImageStorage, HnStorage, SnStorage

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - [%(asctime)s] %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

imstore = ImageStorage()
hnstore = HnStorage()
snstore = SnStorage()

@app.route("/hackernews")
@app.route('/')
def hackernews():
    return render_template('index.html', title='Hacker News',
            news_list=hnstore.get_all())

@app.route("/startupnews")
def startupnews():
    return render_template('index.html', title='Startup News',
            news_list=snstore.get_all())

@app.route('/img/<img_id>')
def image(img_id):
    img = imstore.get(id=img_id)
    if not img:
       abort(404)
    return str(img['raw_data']), 200, {'Content-Type': img['content_type']}

@app.route('/update/<what>')
@app.route('/update')
def update(what=None):
    if request.args.get('key') != os.environ.get('HN_UPDATE_KEY'):
        abort(404)
    if what == 'hackernews' or what is None:
        # Spawn another process so it doesn't
        # account for dyno hours.
        Popen(['python', 'hackernews.py'])
    if what == 'startupnews' or what is None:
        Popen(['python', 'startupnews.py'])
    return 'Great success!'

@app.route('/favicon.ico')
def static_files():
    return send_from_directory(app.static_folder, request.path[1:])

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

