import os
import logging
import psycopg2
import psycopg2.extras

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import (
        create_engine, SQLAlchemyError, Sequence,
        Column, Integer, String, ForeignKey, LargeBinary
    )

logger = logging.getLogger(__name__)

# Receive unicode strings
# see http://initd.org/psycopg/docs/faq.html#problems-with-type-conversions
# psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
# psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)

engine = create_engine(os.environ.get("DATABASE_URL", 
    'postgres://postgres@localhost:5432/postgres')\
            .replace('postgres://', 'postgresql://'), pool_size=10, max_overflow=10)
# Session = scoped_session(sessionmaker(bind=engine))
Session = sessionmaker(bind=engine)

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
    img_id = Column(String, ForeignKey('image.id'))

    image = relationship('image', cascade='delete, delete-orphan')

    def __repr__(self):
        return u"%s<%s>" % (self.title, self.url)

class StartupNewsTable(HackerNewsTable):
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
    img_id = Column(String, ForeignKey('image.id'))

    image = relationship('image', cascade='delete, delete-orphan')

    def __repr__(self):
        return u"%s<%s>" % (self.title, self.url)

class Image(Base):
    __tablename__ = 'image'

    id = Column(Integer, Sequence('image_id_seq'), primary_key=True)
    content_type = Column(String)
    raw_data = Column(LargeBinary)

def sync_db():
    Base.metadata.create_all(engine)

def drop_db():
    Base.metadata.drop_all(engine)

class Storage(object):

    def __init__(self):
        self.pk = self.model.__mapper__.primary_key[0]
        self.session = Session()
        self.tablename = self.model.__tablename__

    def get(self, pk):
        return self.session.query(self.model).get(pk)

    exist = get

    def put(self, **kwargs):
        try:
            self.session.add(self.model(**kwargs))
            self.session.commit()
        # except psycopg2.IntegrityError as e:
        except SQLAlchemyError as e:
            logger.info('Failed to save %s, %s', kwargs[self.pk], e)
            self.session.rollback()

    def update(self, pk, **kwargs):
        try:
            self.session.query(self.model).filter(self.pk==pk).update(kwargs)
            self.session.commit()
        except SQLAlchemyError as e:
            logger.info('Failed to update %s(%s), %s', self.table_name, pk, e)
            self.session.rollback()

    def delete(self, pk):
        try:
            self.session.query(self.model).filter(self.pk==pk).delete()
            self.session.commit()
        except SQLAlchemyError as e:
            logger.info('Failed to delete %s(%s), %s', self.table_name, pk, e)
            self.session.rollback()

    def remove_except(self, keys):
        try:
            self.session.query(self.model).filter(~self.pk.in_(keys)).delete()
            self.session.commit()
        except SQLAlchemyError as e:
            logger.info('Failed to delete %s(%s), %s', self.table_name,
                    ', '.join(keys), e)
            self.session.rollback()

class ImageStorage(Storage):
    table_name = 'image'
    pk = 'id'

    def put(self, **kwargs):
        if 'raw_data' in kwargs:
            kwargs['raw_data'] = psycopg2.Binary(kwargs['raw_data'])
        return super(ImageStorage, self).put(**kwargs)


class HnStorage(Storage):
    model = HackerNewsTable

    def get_all(self):
        self.session.query(self.model).all()

class SnStorage(HnStorage):
    model = StartupNewsTable

if __name__ == '__main__':
    sync_db()

