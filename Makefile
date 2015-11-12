.PHONY: run test initdb dropdb
run: initdb
	# DEBUG=1 python index.py
	python index.py
run-in-docker: initdb
	gunicorn -b 0.0.0.0:5000 -c config.py index:app
run-in-heroku: initdb setcron
	sed -i "s/xxxxxxxxx/${NEW_RELIC_API_KEY}/" config/newrelic.ini
	mkdir -p logs/nginx
	touch /tmp/app-initialized
	[ -f bin/start-nginx ] && bin/start-nginx gunicorn -c config.py index:app || gunicorn --bind 0.0.0.0:$(PORT) -c config.py index:app
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
