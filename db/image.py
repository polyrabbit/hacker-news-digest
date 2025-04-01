# TODO: need a separate model?
import logging
import os
import random
import time

from sqlalchemy import String, column, Values, select

import config
from db import Summary
from db.engine import session_scope

logger = logging.getLogger(__name__)

"""
SELECT v.name 
FROM (VALUES ('c189bad0066ddb74264e7e03fa8b2dda.jpg')) AS v (name) LEFT OUTER JOIN summary ON summary.image_name = v.name 
WHERE summary.image_name IS NULL
"""


def expire():
    start = time.time()
    removed = 0
    all_files = list(os.listdir(config.image_dir))
    random.shuffle(all_files) # avoid checking whole list everytime to reduce transfer cost to DB
    candidates = all_files[:1000]
    for img_files in chunks(candidates, 500):
        values = Values(column('name', String), name='v').data(list(map(lambda x: (x,), img_files)))
        stmt = select(values).join(Summary, Summary.image_name == values.c.name,
                                   isouter=True  # Add this to implement left outer join
                                   ).where(Summary.image_name.is_(None))
        with session_scope() as session:
            for image_name in session.execute(stmt):
                logger.debug(f'removing {image_name[0]}')
                os.remove(os.path.join(config.image_dir, image_name[0]))
                removed += 1
    cost = (time.time() - start) * 1000
    logger.info(f'removed {removed}/{len(candidates)} feature images, cost(ms): {cost:.2f}')


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]
