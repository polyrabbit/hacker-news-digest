import logging
# cStringIO won't let me set name attr on it
from StringIO import StringIO
import datetime
from hashlib import md5

from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from index import db

logger = logging.getLogger(__name__)

session = db.session

class HelperMixin(object):

    @classmethod
    def add(cls, **kwargs):
        """
        Returns primary_key on success
        """
        pk_name = cls.__mapper__.primary_key[0].name
        try:
            obj = cls(**kwargs)
            # TODO should I consider auto_commit?
            session.add(obj)
            session.commit()
            return getattr(obj, pk_name)
        # except SQLAlchemyError:
        except IntegrityError as e:  # if duplicated id, we just use the old one
            session.rollback()
            return e.params[pk_name]
        except Exception:
            logger.exception('Failed to save %s', kwargs.get(pk_name, 'image'))
            session.rollback()

    @classmethod
    def update(cls, pk_value, **kwargs):
        pk = cls.__mapper__.primary_key[0]
        try:
            # NOTE should use filter, not filter_by
            cls.query.filter(pk==pk_value).update(kwargs)
            session.commit()
        except SQLAlchemyError:
            logger.exception('Failed to update %s(%s)', cls.__tablename__, pk.name)
            session.rollback()

    @classmethod
    def delete(cls, pk_value):
        pk = cls.__mapper__.primary_key[0]
        try:
            cls.query.filter(pk==pk_value).delete()
            session.commit()
        except SQLAlchemyError:
            logger.exception('Failed to delete %s from %s', pk.name, cls.__tablename__)
            session.rollback()

    @classmethod
    def remove_except(cls, keys):
        pk = cls.__mapper__.primary_key[0]
        try:
            rcnt = -1
            # if not keys:
                  # TODO query.delete will fire a delete from, which won't delete
                  # related image, have to delete them one by one
            #     rcnt = cls.query.delete() - 1
            # else:
            for rcnt, obsolete in enumerate(cls.query.filter(~pk.in_(keys))):
                session.delete(obsolete)
            logger.info('Removed %s items from %s', rcnt+1, cls.__tablename__)
            session.commit()
        except SQLAlchemyError:
            logger.exception('Failed to clean old urls in %s', cls.__tablename__)
            session.rollback()

class HackerNews(db.Model, HelperMixin):
    __tablename__ = 'hackernews'

    rank = db.Column(db.Integer)
    title = db.Column(db.String)
    url = db.Column(db.String, primary_key=True)
    comhead = db.Column(db.String)
    score = db.Column(db.Integer)
    author = db.Column(db.String)
    author_link = db.Column(db.String)
    submit_time = db.Column(db.String)
    comment_cnt = db.Column(db.Integer)
    comment_url = db.Column(db.String)
    summary = db.Column(db.String)
    img_id = db.Column(db.String, db.ForeignKey('image.id', ondelete='CASCADE'))
    favicon = db.Column(db.String)

    image = db.relationship('Image', cascade='delete')

    def __repr__(self):
        return u"%s<%s>" % (self.title, self.url)

# TODO too verbose to define two times,
# find a better way
class StartupNews(db.Model, HelperMixin):
    __tablename__ = 'startupnews'

    rank = db.Column(db.Integer)
    title = db.Column(db.String)
    url = db.Column(db.String, primary_key=True)
    comhead = db.Column(db.String)
    score = db.Column(db.Integer)
    author = db.Column(db.String)
    author_link = db.Column(db.String)
    submit_time = db.Column(db.String)
    comment_cnt = db.Column(db.Integer)
    comment_url = db.Column(db.String)
    summary = db.Column(db.String)
    img_id = db.Column(db.String, db.ForeignKey('image.id', ondelete='CASCADE'))
    favicon = db.Column(db.String)

    image = db.relationship('Image', cascade='delete')

    def __repr__(self):
        return u"%s<%s>" % (self.title, self.url)

def md5_img(context):
    return md5(context.current_parameters['raw_data']).hexdigest()

class Image(db.Model, HelperMixin):
    __tablename__ = 'image'

    id = db.Column(db.String, default=md5_img, primary_key=True)
    content_type = db.Column(db.String)
    raw_data = db.Column(db.LargeBinary)

    def __init__(self, content_type, raw_data):
        self.content_type = content_type
        self.raw_data = raw_data

    def __repr__(self):
        return u"%s<%s>" % (self.id, self.content_type)

    def makefile(self):
        file = StringIO(self.raw_data)
        file.name = __file__
        return file

class LastUpdated(db.Model):
    __tablename__ = 'last_updated'

    table_name = db.Column(db.String, primary_key=True)
    time_stamp = db.Column(db.DateTime, default=datetime.datetime.now)

    def __init__(self, tn, ts):
        self.table_name = tn
        self.time_stamp = ts

    @classmethod
    def update(cls, tn):
       session.merge(cls(tn, datetime.datetime.now()))
       try:
            session.commit()
       except SQLAlchemyError:
           logger.exception('Failed to update %s', tn)
           session.rollback()

    @classmethod
    def get(cls, tn):
        obj = cls.query.get(tn)
        if obj:
            return obj.time_stamp
        return None

    def __repr__(self):
        return u"%s<%s>" % (self.table_name, self.time_stamp)

# gunicorn causes race condition when spawning multi processes
# db.create_all()

import threading, time
def fun():
    while True:
        print '-'*10, db.engine.pool, db.engine.pool.status()
        time.sleep(3)

# t = threading.Thread(target=fun)
# t.daemon = True
# t.start()

