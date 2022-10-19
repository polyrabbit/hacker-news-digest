export NEW_RELIC_CONFIG_FILE=config/newrelic.ini
export BLUEWARE_CONFIG_FILE=config/blueware.ini 

.PHONY: run test initdb dropdb gh_pages
run: initdb
	# DEBUG=1 python index.py
	python index.py

run-in-docker: initdb
	gunicorn -b 0.0.0.0:5000 -c config.py index:app

run-in-heroku: initdb setcron initnewrelic
	mkdir -p logs/nginx
	touch /tmp/app-initialized
	# blueware-admin run-program 
	[ -f bin/start-nginx ] && \
		bin/start-nginx \
		newrelic-admin run-program \
		gunicorn -c config.py index:app || \
		newrelic-admin run-program \
		gunicorn --bind 0.0.0.0:$(PORT) -c config.py index:app

gh_pages:
	rm -rf output
	mkdir -p output/image
	python publish.py
	cp -r static output/static

test:
	python -m unittest discover ./test

dropdb:
	python -c 'from models import db; db.drop_all()'

initdb:
	-createuser postgres;
	-echo create database hndigest ENCODING "'UTF8'" TEMPLATE template0 | sudo -n -u postgres psql
	-echo create database hndigest ENCODING "'UTF8'" TEMPLATE template0 | sudo -n su - postgres -c psql
	python -c 'from models import db; db.create_all()'

setcron:
	while true; do sleep 600; curl -s -H "User-Agent: Update from internal" -L "http://localhost:$(PORT)/update" -X POST `[ -z $${HN_UPDATE_KEY} ] && echo '' || echo -d key=$${HN_UPDATE_KEY}`; done &

initnewrelic:
	pip install newrelic
	sed -i "s/xxxxxxxxx/${NEW_RELIC_API_KEY}/" ${NEW_RELIC_CONFIG_FILE}

initoneapm:
	pip install -i http://pypi.oneapm.com/simple --trusted-host pypi.oneapm.com blueware
	sed -i "s/xxxxxxxxx/${ONEAPM_API_KEY}/" ${BLUEWARE_CONFIG_FILE}
