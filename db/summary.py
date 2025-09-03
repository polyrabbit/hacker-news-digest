import logging
import time
from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy import String, TIMESTAMP, select, delete
from sqlalchemy.orm import mapped_column

import config
from db.engine import Base, session_scope

logger = logging.getLogger(__name__)
CONTENT_TTL = 1 * 24 * 60 * 60


class Model(Enum):
    PREFIX = 'Prefix'
    FULL = 'Full'
    EMBED = 'Embed'
    TRANSFORMER = 'GoogleT5'
    LLAMA = 'Llama'
    STEP = 'Step'
    GEMMA = 'Gemma'
    QWEN = 'Qwen'
    OPENAI = 'OpenAI'

    def can_truncate(self):
        return self not in (Model.OPENAI, Model.EMBED)

    def local_llm(self):
        return self in (Model.LLAMA, Model.TRANSFORMER)

    def is_finally(self) -> bool:  # already best, no need to try other models
        return self in (Model.EMBED, Model.OPENAI, Model.GEMMA, Model.LLAMA, Model.STEP, Model.QWEN)

    def need_escape(self):
        return self in (Model.OPENAI, Model.GEMMA, Model.LLAMA, Model.QWEN)

    @classmethod
    def from_value(cls, value):
        try:
            return cls(value)
        except ValueError as e:
            logger.warning(f'{e}')
            return Model.FULL


class Summary(Base):
    __tablename__ = 'summary'

    url = mapped_column(String(4096), primary_key=True)
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

    def __eq__(self, other):
        return repr(self) == repr(other)

    def get_summary_model(self) -> Model:
        return Model.from_value(self.model)


def get(url) -> Summary:
    if config.disable_summary_cache:
        return Summary(url)
    with session_scope() as session:
        summary = session.get(Summary, url)  # Try to leverage the identity map cache
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
    with session_scope() as session:
        db_summary = session.merge(db_summary)
    return db_summary


def filter_url(url_list: list[str]) -> set[str]:
    # use `all()` to populate the Identity Map so that following `get` can read from cache
    with session_scope() as session:
        summaries = session.scalars(select(Summary).where(Summary.url.in_(url_list))).all()
        assert len(session.identity_map) == len(summaries)
    return set(s.url for s in summaries)


def expire():
    start = time.time()
    stmt = delete(Summary).where(
        Summary.access < datetime.utcnow() - timedelta(seconds=config.summary_ttl))
    with session_scope() as session:
        result = session.execute(stmt)
        deleted = result.rowcount
        logger.info(f'evicted {result.rowcount} summary items')

        stmt = delete(Summary).where(
            Summary.access < datetime.utcnow() - timedelta(seconds=CONTENT_TTL),
            Summary.model.in_((Model.PREFIX.value, Model.FULL.value, Model.EMBED.value)))
        result = session.execute(stmt)
        cost = (time.time() - start) * 1000
        logger.info(f'evicted {result.rowcount} full content items, cost(ms): {cost:.2f}')

    return deleted + result.rowcount
