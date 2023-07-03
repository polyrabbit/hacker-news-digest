import logging
from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy import String, TIMESTAMP, select, delete
from sqlalchemy.orm import mapped_column

import config
from db.engine import Base, session

logger = logging.getLogger(__name__)
CONTENT_TTL = 1 * 24 * 60 * 60


class Model(Enum):
    PREFIX = 'Prefix'
    FULL = 'Full'
    EMBED = 'Embed'
    TRANSFORMER = 'GoogleT5'
    OPENAI = 'OpenAI'

    def can_truncate(self):
        return self not in (Model.OPENAI, Model.EMBED)

    def need_escape(self):
        return self in (Model.OPENAI,)


class Summary(Base):
    __tablename__ = 'summary'

    url = mapped_column(String(1024), primary_key=True)
    summary = mapped_column(String(65535))
    model = mapped_column(String(16), default=Model.FULL.value)
    birth = mapped_column(TIMESTAMP, default=datetime.utcnow)

    favicon = mapped_column(String(65535), nullable=True)
    image_name = mapped_column(String(65535), nullable=True, index=True)
    image_json = mapped_column(String(65535), nullable=True)

    def __init__(self, url, summary='', model=Model.FULL, **kw):
        super().__init__(**kw)
        self.url = url
        self.summary = summary
        self.model = model.value

    def __repr__(self):
        return f'<{self.url} - {self.summary} - {self.model} - {self.birth} - {self.access}> - {self.favicon} - {self.image_name}'

    def get_summary_model(self):
        try:
            return Model(self.model)
        except ValueError as e:
            logger.warning(f'{e}')
            return Model.FULL


def get(url) -> Summary:
    if config.disable_summary_cache:
        return Summary(url)
    stmt = select(Summary).where(Summary.url == url)
    # if model:
    #     stmt = stmt.where(Summary.model == model.value)
    summary = session.scalars(stmt).first()
    return summary or Summary(url)


def put(db_summary: Summary) -> Summary:
    db_summary.access = datetime.utcnow()
    db_summary.summary = db_summary.summary[:Summary.summary.type.length]
    if db_summary.favicon:
        db_summary.favicon = db_summary.favicon[:Summary.favicon.type.length]
    if db_summary.image_name:
        db_summary.image_name = db_summary.image_name[:Summary.image_name.type.length]
    if db_summary.image_json:
        db_summary.image_json = db_summary.image_json[:Summary.image_json.type.length]
    db_summary = session.merge(db_summary)
    session.commit()
    return db_summary


def expire():
    stmt = delete(Summary).where(
        Summary.access < datetime.utcnow() - timedelta(seconds=config.summary_ttl))
    result = session.execute(stmt)
    deleted = result.rowcount
    logger.info(f'evicted {result.rowcount} summary items')

    stmt = delete(Summary).where(
        Summary.access < datetime.utcnow() - timedelta(seconds=CONTENT_TTL),
        Summary.model.not_in((Model.OPENAI.value, Model.TRANSFORMER.value)))
    result = session.execute(stmt)
    logger.info(f'evicted {result.rowcount} content items')
    session.commit()
    return deleted + result.rowcount
