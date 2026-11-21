import logging
import re

import config

logger = logging.getLogger(__name__)

_llm = None  # lazy load
_SUMMARY_SYSTEM_PROMPT = (
    'You summarize Hacker News articles for a technical audience. '
    'Return exactly two concise English sentences, no more than 250 characters. '
    'Output plain text only, with no heading, markdown, or reasoning.'
)
_TRANSLATE_SYSTEM_PROMPT = '''你是资深的中文科技媒体编辑，负责把 Hacker News 文章的英文标题和摘要翻译成简体中文。
要求：
- 忠实原意，不增删信息；数字、单位、版本号和专有名词必须准确。
- 先理解整句意思，再按中文的表达习惯重新组织语序，读起来要像中文科技媒体的原创内容，不要翻译腔，不要逐词直译。
- 标题里的俚语、双关和名词活用要意译，不要生硬套用字面意思。
- 术语使用中文技术社区的惯用译法；产品名、公司名、项目名、代码、命令保留英文原文；有通用中文译名的人名、地名、概念用通用译名。
- 标题简洁有力；Show HN、Ask HN、Launch HN 等前缀原样保留，原文没有的不要添加。
- 按原文的“标题：”和“摘要：”逐行输出译文，不要输出其他内容。'''
_TRANSLATE_EXAMPLE = (
    '标题：We cut our cloud bill by 70% by leaving Kubernetes\n'
    '摘要：The author describes how their team moved from a managed Kubernetes cluster to a handful of bare-metal servers. '
    'They argue that most startups overestimate their scaling needs and pay a heavy price in operational complexity.',
    '标题：离开 Kubernetes 后，我们的云账单降了 70%\n'
    '摘要：作者介绍了团队如何从托管的 Kubernetes 集群迁移到几台物理服务器上。'
    '他认为，大多数初创公司都高估了自己的扩展需求，并为此付出了高昂的运维复杂度代价。',
)
# Chinese typesetting convention: a space between Han characters and Latin letters or digits
_HAN_LATIN_GAP = re.compile(r'(?<=[\u4e00-\u9fff])(?=[A-Za-z0-9])|(?<=[A-Za-z0-9%])(?=[\u4e00-\u9fff])')
_SAMPLING = dict(temperature=0.2, top_p=0.8, top_k=20, repeat_penalty=1.05,
                 stream=False, stop=['<|im_end|>', '<|endoftext|>'])


def _get_llm():
    global _llm
    if _llm is None:
        if not config.local_qwen_path:
            raise RuntimeError('LOCAL_QWEN_PATH is not set')
        try:
            from llama_cpp import Llama
        except ImportError as e:
            raise RuntimeError('llama-cpp-python is required for local Qwen') from e

        _llm = Llama(
            model_path=config.local_qwen_path,
            # A 4 vCPU runner processes only ~10 prompt tokens/s, a 6k context lets one call finish within a 20-minute run.
            n_ctx=6144,
            n_threads=4,
            n_threads_batch=4,
            use_mmap=True,
            verbose=False,
        )
    return _llm


def _truncate_content(llm, content):
    # Leave room for the chat template, system prompt, and generated answer.
    reserve = 256
    max_content_tokens = max(llm.n_ctx() - reserve, 1)
    tokens = llm.tokenize(content.encode('utf-8'), add_bos=False)
    if len(tokens) <= max_content_tokens:
        return content
    logger.info('Truncate local Qwen input from %d to %d tokens',
                len(tokens), max_content_tokens)
    return llm.detokenize(tokens[:max_content_tokens]).decode('utf-8', errors='ignore').strip()


def _clean_response(response):
    answer = (response or '').strip()
    answer = re.sub(r'<think>.*?</think>', '', answer, flags=re.DOTALL).strip()
    if '</think>' in answer:
        answer = answer.rsplit('</think>', 1)[-1].strip()
    if '<think>' in answer:
        answer = answer.split('<think>', 1)[0].strip()
    answer = answer.replace('**', '').strip()
    answer = re.sub(r'^(?:#+\s*)?(?:summary\s*:?)', '', answer,
                    flags=re.IGNORECASE).strip()
    answer = re.sub(r'\s+', ' ', answer)
    return answer.strip()


def summarize_by_local_qwen(content: str) -> str:
    llm = _get_llm()
    content = _truncate_content(llm, content.strip())
    if not content:
        return ''

    response = llm.create_chat_completion(
        messages=[
            {'role': 'system', 'content': _SUMMARY_SYSTEM_PROMPT},
            # Qwen3 uses this suffix to select its non-thinking mode.
            {'role': 'user', 'content': f'{content}\n/no_think'},
        ],
        max_tokens=96,
        **_SAMPLING,
    )
    answer = response['choices'][0]['message'].get('content', '')
    return _clean_response(answer)


def translate_by_local_qwen(title: str, summary: str = '') -> tuple[str, str]:
    """Translate a title and an optional summary into simplified Chinese together, so they share the same terms."""
    source = f'标题：{title}' + (f'\n摘要：{summary}' if summary else '')
    example, answer = _TRANSLATE_EXAMPLE
    response = _get_llm().create_chat_completion(
        # A fixed prefix lets llama.cpp reuse its KV cache across calls
        messages=[
            {'role': 'system', 'content': _TRANSLATE_SYSTEM_PROMPT},
            {'role': 'user', 'content': f'{example}\n/no_think'},
            {'role': 'assistant', 'content': answer},
            {'role': 'user', 'content': f'{source}\n/no_think'},
        ],
        max_tokens=512,
        **_SAMPLING,
    )
    choice = response['choices'][0]
    answer = re.sub(r'<think>.*?</think>', '', choice['message'].get('content') or '', flags=re.DOTALL).strip()
    if choice['finish_reason'] != 'stop' or not (m := re.fullmatch(r'标题[：:](.*?)(?:\n摘要[：:](.*))?', answer, re.DOTALL)):
        return '', ''  # cut off or malformed, retry next time
    title_zh, summary_zh = (_HAN_LATIN_GAP.sub(' ', (s or '').strip()) for s in m.groups())
    return title_zh, summary_zh if re.search(r'[\u4e00-\u9fff]', summary_zh) else ''  # not an English echo
