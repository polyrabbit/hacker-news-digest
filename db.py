import logging
# cStringIO won't let me set name attr on it
from StringIO import StringIO


import config
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import (
        create_engine, Sequence,
        Column, Integer, String, ForeignKey, LargeBinary
    )

logger = logging.getLogger(__name__)

# Receive unicode strings
# see http://initd.org/psycopg/docs/faq.html#problems-with-type-conversions
# psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
# psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)

engine = create_engine(config.db_url, pool_size=config.db_pool_size,
        max_overflow=config.db_max_overflow)
# scoped_session ensures I get the same session whenever I call it.
Session = scoped_session(sessionmaker(bind=engine))
# Session = sessionmaker(bind=engine)

Base = declarative_base()

class HackerNewsTable(Base):
    __tablename__ = 'hackernews'

    rank = Column(Integer)
    title = Column(String)
    url = Column(String, primary_key=True)
    comhead = Column(String)
    score = Column(Integer)
    author = Column(String)
    author_link = Column(String)
    submit_time = Column(String)
    comment_cnt = Column(Integer)
    comment_url = Column(String)
    summary = Column(String)
    img_id = Column(Integer, ForeignKey('image.id'))

    image = relationship('Image', cascade='delete')

    def __repr__(self):
        return u"%s<%s>" % (self.title, self.url)

# TODO too verbose to define two times,
# find a better way
class StartupNewsTable(Base):
    __tablename__ = 'startupnews'

    rank = Column(Integer)
    title = Column(String)
    url = Column(String, primary_key=True)
    comhead = Column(String)
    score = Column(Integer)
    author = Column(String)
    author_link = Column(String)
    submit_time = Column(String)
    comment_cnt = Column(Integer)
    comment_url = Column(String)
    summary = Column(String)
    img_id = Column(Integer, ForeignKey('image.id'))

    image = relationship('Image', cascade='delete')

    def __repr__(self):
        return u"%s<%s>" % (self.title, self.url)

class Image(Base):
    __tablename__ = 'image'

    id = Column(Integer, Sequence('image_id_seq'), primary_key=True)
    content_type = Column(String)
    raw_data = Column(LargeBinary)

    def __repr__(self):
        return u"%s<%s>" % (self.id, self.content_type)

    def makefile(self):
        file = StringIO(self.raw_data)
        file.name = __file__
        return file

def sync_db():
    Base.metadata.create_all(engine)

def drop_db():
    Base.metadata.drop_all(engine)

import threading, time
def fun():
    while True:
        print '-'*10, engine.pool, engine.pool.status()
        time.sleep(3)

t = threading.Thread(target=fun)
t.daemon = True
# t.start()

class Storage(object):

    def __init__(self):
        self.pk = self.model.__mapper__.primary_key[0]
        self.session = Session()
        self.table_name = self.model.__tablename__

    def get(self, pk):
        return self.session.query(self.model).get(pk)

    exist = get

    def put(self, **kwargs):
        """
        Returns primary_key on success
        """
        try:
            obj = self.model(**kwargs)
            self.session.add(obj)
            self.session.commit()
            return getattr(obj, self.pk.name)
        except SQLAlchemyError:
            logger.exception('Failed to save %s', kwargs[self.pk.name])
            self.session.rollback()

    def update(self, pk, **kwargs):
        try:
            self.session.query(self.model).filter(self.pk==pk).update(kwargs)
            self.session.commit()
        except SQLAlchemyError:
            logger.exception('Failed to update %s(%s)', self.table_name, pk)
            self.session.rollback()

    def delete(self, pk):
        try:
            self.session.query(self.model).filter(self.pk==pk).delete()
            self.session.commit()
        except SQLAlchemyError:
            logger.exception('Failed to delete %s from %s', pk, self.table_name)
            self.session.rollback()

    def remove_except(self, keys):
        if not keys:
            logger.warning("Get a empty key to remove_except")
            return
        try:
            rcnt = -1
            for rcnt, obsolete in enumerate(self.session.query(self.model).filter(~self.pk.in_(keys))):
                self.session.delete(obsolete)
            logger.info('Removed %s items from %s', rcnt+1, self.table_name)
            self.session.commit()
        except SQLAlchemyError:
            logger.exception('Failed to clean old urls in %s', self.table_name)
            self.session.rollback()

    def __del__(self):
        self.session.close()

class ImageStorage(Storage):
    model = Image

class HnStorage(Storage):
    model = HackerNewsTable

    def get_all(self):
        return self.session.query(self.model).order_by('rank').all()

class SnStorage(HnStorage):
    model = StartupNewsTable

sync_db()
# drop_db()

