import re

_SYSTEM_PROMPT = '''你是资深的中文科技媒体编辑，负责把 Hacker News 文章的英文标题和摘要翻译成简体中文。
要求：
- 忠实原意，不增删信息；数字、单位、版本号和专有名词必须准确。
- 先理解整句意思，再按中文的表达习惯重新组织语序，读起来要像中文科技媒体的原创内容，不要翻译腔，不要逐词直译。
- 标题里的俚语、双关和名词活用要意译，不要生硬套用字面意思。
- 术语使用中文技术社区的惯用译法；产品名、公司名、项目名、代码、命令保留英文原文；有通用中文译名的人名、地名、概念用通用译名。
- 标题简洁有力；Show HN、Ask HN、Launch HN 等前缀原样保留，原文没有的不要添加。
- 按原文的“标题：”和“摘要：”逐行输出译文，不要输出其他内容。'''
_EXAMPLE = (
    '标题：We cut our cloud bill by 70% by leaving Kubernetes\n'
    '摘要：The author describes how their team moved from a managed Kubernetes cluster to a handful of bare-metal servers. '
    'They argue that most startups overestimate their scaling needs and pay a heavy price in operational complexity.',
    '标题：离开 Kubernetes 后，我们的云账单降了 70%\n'
    '摘要：作者介绍了团队如何从托管的 Kubernetes 集群迁移到几台物理服务器上。'
    '他认为，大多数初创公司都高估了自己的扩展需求，并为此付出了高昂的运维复杂度代价。',
)
# Chinese typesetting convention: a space between Han characters and Latin letters or digits
_HAN_LATIN_GAP = re.compile(r'(?<=[\u4e00-\u9fff])(?=[A-Za-z0-9])|(?<=[A-Za-z0-9%])(?=[\u4e00-\u9fff])')


def messages(title: str, summary: str = '', suffix: str = '') -> list[dict]:
    """Chat messages that translate a title and an optional summary together, so they share the same terms."""
    source = f'标题：{title}' + (f'\n摘要：{summary}' if summary else '')
    example, answer = _EXAMPLE
    # A fixed prefix lets the inference engine reuse its KV cache across calls
    return [
        {'role': 'system', 'content': _SYSTEM_PROMPT},
        {'role': 'user', 'content': example + suffix},
        {'role': 'assistant', 'content': answer},
        {'role': 'user', 'content': source + suffix},
    ]


def parse(answer: str) -> tuple[str, str]:
    answer = re.sub(r'<think>.*?</think>', '', answer or '', flags=re.DOTALL).strip()
    if not (m := re.fullmatch(r'标题[：:](.*?)(?:\n摘要[：:](.*))?', answer, re.DOTALL)):
        return '', ''  # malformed, retry next time
    title_zh, summary_zh = (_HAN_LATIN_GAP.sub(' ', (s or '').strip()) for s in m.groups())
    return title_zh, summary_zh if re.search(r'[\u4e00-\u9fff]', summary_zh) else ''  # not an English echo
