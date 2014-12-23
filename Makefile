.PHONY: run test drop
run:
	DEBUG=1 python index.py
run-in-heroku:
	sed -i "s/xxxxxxxxx/${NEW_RELIC_API_KEY}/" config/newrelic.ini
	mkdir -p logs/nginx
	touch /tmp/app-initialized
	bin/start-nginx gunicorn -c config.py index:app
test:
	python -m unittest discover ./test
drop:
	python -c 'from models import db; db.drop_all()'
