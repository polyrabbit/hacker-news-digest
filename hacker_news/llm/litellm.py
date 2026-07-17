import json
import logging
import re
import time

import config

logger = logging.getLogger(__name__)


def _import_litellm():
    try:
        import litellm
        return litellm
    except ImportError:
        raise ImportError(
            "litellm is required. Install it with: pip install 'litellm>=1.83.0'"
        )


def _truncate_content(text: str, max_chars: int = 30000) -> str:
    """Simple content truncation. Unlike sanitize_for_openai, this doesn't
    depend on the openai SDK's global state (api_base)."""
    text = text.replace('```', ' ').strip()
    if len(text) > max_chars:
        text = text[:max_chars]
    return text.strip('.').strip()


def _clean_summary(answer: str) -> str:
    """Clean up a summarization response (English-only output expected)."""
    if '</think>' in answer:
        answer = answer.split('</think>', 1)[-1].strip()
    for line in answer.split('\n'):
        if not line.strip():
            continue
        if 'summary' in line.lower() and line.strip()[-1] == ':':
            continue
        answer = line
        break
    answer = re.sub(r'^[^a-zA-Z0-9]+', '', answer)
    answer = answer.replace('**', ' ')
    answer = re.sub(r'^summary:?', '', answer, flags=re.IGNORECASE)
    return answer.strip()


def _clean_translation(answer: str) -> str:
    """Clean up a translation response (preserves non-Latin characters)."""
    if '</think>' in answer:
        answer = answer.split('</think>', 1)[-1].strip()
    answer = answer.replace('**', ' ')
    return answer.strip()


def call_litellm(content: str, sys_prompt: str, clean_fn=None) -> str:
    litellm = _import_litellm()

    if not config.litellm_model:
        raise ValueError("LITELLM_MODEL environment variable is not set")

    start_time = time.time()
    content = _truncate_content(content)

    kwargs = {
        'model': config.litellm_model,
        'messages': [
            {'role': 'system', 'content': sys_prompt},
            {'role': 'user', 'content': content},
        ],
        'stream': False,
        'temperature': 0,
        'n': 1,
        'timeout': 30,
        'drop_params': True,
    }
    if config.litellm_api_key:
        kwargs['api_key'] = config.litellm_api_key

    try:
        resp = litellm.completion(**kwargs)
    except litellm.AuthenticationError as e:
        logger.error(f'LiteLLM authentication failed: {e}')
        raise
    except litellm.NotFoundError as e:
        logger.error(f'LiteLLM model not found: {e}')
        raise
    except litellm.RateLimitError as e:
        logger.warning(f'LiteLLM rate limited: {e}')
        raise
    except litellm.Timeout as e:
        logger.error(f'LiteLLM request timed out: {e}')
        raise
    except litellm.APIConnectionError as e:
        logger.error(f'LiteLLM connection error: {e}')
        raise

    resp_dict = resp.model_dump()

    logger.warning(f'took {time.time() - start_time}s to generate: '
                   f'{json.dumps(resp_dict, sort_keys=True, indent=2, ensure_ascii=False)}')

    choices = resp_dict.get('choices', [])
    if not choices:
        logger.error('LiteLLM returned empty choices')
        return ''

    message = choices[0].get('message', {})
    answer = (message.get('content') or '').strip()

    if not answer:
        logger.warning('LiteLLM returned empty content')
        return ''

    if clean_fn:
        return clean_fn(answer)
    return answer


def summarize_by_litellm(content: str) -> str:
    return call_litellm(
        content,
        "You are a helpful summarizer. Please think step by step to summarize all user's input in 2 concise English sentences. Ensure the summary does not exceed 250 "
        "characters. Provide response in plain text format without any Markdown formatting.",
        clean_fn=_clean_summary,
    )


def translate_by_litellm(content: str, lang: str) -> str:
    return call_litellm(
        content,
        f"You are a helpful translator. Translate user's input into {lang}.",
        clean_fn=_clean_translation,
    )
