.PHONY: run test drop
run:
	DEBUG=1 python index.py
run-in-heroku:
	sed -i "s/xxxxxxxxx/${NEW_RELIC_API_KEY}/" config/newrelic.ini
	mkdir -p logs/nginx
	touch /tmp/app-initialized
	NEW_RELIC_CONFIG_FILE=config/newrelic.ini bin/start-nginx newrelic-admin run-program gunicorn -c config.py index:app
test:
	python -m unittest discover ./test
drop:
	python -c 'from models import db; db.drop_all()'	
