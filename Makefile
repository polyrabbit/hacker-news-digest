.PHONY: run test drop
run:
	DEBUG=1 python index.py
run-in-heroku:
	touch /tmp/app-initialized
	bin/start-nginx gunicorn -c config.py index:app
test:
	python -m unittest discover ./test
drop:
	python -c 'from models import db; db.drop_all()'	
