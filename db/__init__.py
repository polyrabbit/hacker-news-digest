from db.engine import engine, Base
from db.summary import Summary
from db.translation import Translation


def init_db():
    Base.metadata.create_all(engine, checkfirst=True)
    translation.add('Hacker News Summary', 'Hacker News 摘要', 'zh')
    translation.add('Translate', '翻译', 'zh')
