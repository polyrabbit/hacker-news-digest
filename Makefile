.PHONY: run test drop
run:
	DEBUG=1 python index.py
run-in-heroku:
	bin/start-nginx gunicorn -c config.py index:app && touch /tmp/app-initialized
test:
	python -m unittest discover ./test
drop:
	python -c 'from models import db; db.drop_all()'	
