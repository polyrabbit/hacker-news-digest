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
            # GitHub ubuntu-latest: 4 vCPU / 16 GB RAM; keep enough headroom for the site job.
            n_ctx=10240,
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
        temperature=0.2,
        top_p=0.8,
        top_k=20,
        repeat_penalty=1.05,
        max_tokens=96,
        stream=False,
        stop=['<|im_end|>', '<|endoftext|>'],
    )
    answer = response['choices'][0]['message'].get('content', '')
    return _clean_response(answer)
