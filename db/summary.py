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
    OPENAI = 'OpenAI'
    TRANSFORMER = 'GoogleT5'

    def can_truncate(self):
        return self not in (Model.OPENAI, Model.EMBED)

    def need_escape(self):
        return self in (Model.OPENAI,)


class Summary(Base):
    __tablename__ = 'summary'

    url = mapped_column(String(1024), primary_key=True)
    summary = mapped_column(String(65535))
    model = mapped_column(String(16))
    birth = mapped_column(TIMESTAMP, default=datetime.utcnow)

    def __repr__(self):
        return f'<{self.url} - {self.summary} - {self.model} - {self.birth} - {self.access}>'


def get(url, model=None):
    if config.disable_summary_cache:
        return ''
    stmt = select(Summary).where(Summary.url == url)
    if model:
        stmt = stmt.where(Summary.model == model.value)
    summary = session.scalars(stmt).first()
    if summary:
        summary.access = datetime.utcnow()
        session.commit()
        return summary.summary
    return ''


def add(url, summary, model):
    if not summary or not url:
        return
    summary = Summary(url=url, summary=summary, model=model.value, access=datetime.utcnow())
    session.merge(summary)
    session.commit()


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
