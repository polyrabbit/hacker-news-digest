import datetime
import logging
import time
from contextlib import contextmanager
from sqlalchemy import create_engine, TIMESTAMP, event, Engine
from sqlalchemy.orm import DeclarativeBase, mapped_column, Session
import config

logger = logging.getLogger(__name__)
engine = create_engine(config.DATABASE_URL, echo=config.DATABASE_ECHO_SQL)  # lazy connection

session = Session(engine)


@contextmanager
def session_scope(defer_commit: bool = False) -> Session:
    """Provide a transactional scope around a series of operations."""
    try:
        yield session
        if not defer_commit:
            session.commit()
    except:
        session.rollback()
        raise
    # finally:
    #     session.close()


class Base(DeclarativeBase):
    access = mapped_column(TIMESTAMP, default=datetime.datetime.utcnow)


@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault("query_start_time", []).append(time.time())


@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    cost = (time.time() - conn.info["query_start_time"].pop(-1)) * 1000
    if cost >= config.SLOW_SQL_MS:
        logger.warning(f'Slow sql {statement}, cost(ms): {cost:.2f}')
