export NEW_RELIC_CONFIG_FILE=config/newrelic.ini
export BLUEWARE_CONFIG_FILE=config/blueware.ini 

.PHONY: run test initdb dropdb gh_pages minify_static hash_static
run: initdb
	# DEBUG=1 python index.py
	python index.py

run-in-docker: initdb
	gunicorn -b 0.0.0.0:5000 -c config.py index:app

gh_pages:
	#find output -maxdepth 1 -type f -delete
	rm -rf output/static
	python publish.py
	cp -r static output/static
	cp static/ads.txt output/ads.txt
	ln -sf index.html output/hackernews  # backward compatibility
	ln -sf feed.xml output/feed
	ln -sf static/favicon.ico output/favicon.ico
	$(MAKE) hash_static
	$(MAKE) minify_static

test: initdb
	python -m unittest

dropdb:
	python -c 'from models import db; db.drop_all()'

initdb:
	python -c 'from db import init_db; init_db()'

setcron:
	while true; do sleep 600; curl -s -H "User-Agent: Update from internal" -L "http://localhost:$(PORT)/update" -X POST `[ -z $${HN_UPDATE_KEY} ] && echo '' || echo -d key=$${HN_UPDATE_KEY}`; done &

minify_static:
	@which minify > /dev/null || { sudo apt-get update; sudo apt-get install --no-install-recommends --yes minify; }
	minify -v --mime=text/html --html-keep-document-tags --html-keep-quotes --html-keep-end-tags -r output --match='index' -o .
	minify -v --mime=text/css -r output --match='style' -o .
	minify -v --mime=application/javascript -r output --match='hn' -o .

cssname = $(shell md5sum static/css/style.css | cut -c1-10)
jsname = $(shell md5sum static/js/hn.js | cut -c1-10)

output/static/css/style.$(cssname).css: output/static/css/style.css
	cp output/static/css/style.css output/static/css/style.$(cssname).css

output/static/js/hn.$(jsname).js: output/static/js/hn.js
	cp output/static/js/hn.js output/static/js/hn.$(jsname).js

hash_static: output/static/css/style.$(cssname).css output/static/js/hn.$(jsname).js output/index.html
	find output -name '*.html' -print0 | xargs -0 sed -i 's/style\.css/style.$(cssname).css/g'
	find output -name '*.html' -print0 | xargs -0 sed -i 's/hn\.js/hn.$(jsname).js/g'