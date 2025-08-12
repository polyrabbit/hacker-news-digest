import json
import logging
import re
import time
from json import JSONDecodeError

import openai
import tiktoken
import config
from db.summary import Model

logger = logging.getLogger(__name__)


def context_limit():
    model = config.openai_model
    if '128k' in model:
        return 128 * 1024
    if '32k' in model or 'mistral-7b' in model:
        return 32 * 1024
    if '16k' in model:
        return 16 * 1024
    # if 'gemma' in model or 'llama' in model or '8192' in model:
    #     return 8 * 1024
    if 'groq' in openai.api_base:
        return 6000  # tokens per minute (TPM) limit: 6000
    return 8 * 1024


def model_family() -> Model:
    if 'llama' in config.openai_model:
        return Model.LLAMA
    if 'gemma' in config.openai_model:
        return Model.GEMMA
    if 'step' in config.openai_model:
        return Model.STEP
    if 'qwen' in config.openai_model:
        return Model.QWEN
    return Model.OPENAI


def sanitize_for_openai(text, overhead):
    text = text.replace('```', ' ').strip()  # in case of prompt injection

    limit = context_limit()
    # one token generally corresponds to ~4 characters, from https://platform.openai.com/tokenizer
    if model_family() in [Model.LLAMA, Model.GEMMA, Model.QWEN]:
        if len(text) > (limit - overhead) * 4:
            text = text[:int((limit - overhead) * 4)]
    elif len(text) > limit * 2:
        try:
            enc = tiktoken.encoding_for_model(config.openai_model)  # We have openai compatible apis now
        except KeyError:
            enc = tiktoken.encoding_for_model('gpt-3.5-turbo')
        tokens = enc.encode(text)
        if len(tokens) > limit - overhead:  # 4096: model's context limit
            text = enc.decode(tokens[:limit - overhead])
    return text.strip(".").strip()


def sanitize_title(title):
    return title.replace('"', "'").replace('\n', ' ').strip()


def call_openai_family(content: str, sys_prompt: str) -> str:
    start_time = time.time()

    # 200: function + prompt tokens (to reduce hitting rate limit)
    content = sanitize_for_openai(content, overhead=200)

    # title = sanitize_title(self.title) or 'no title'
    # Hope one day this model will be clever enough to output correct json
    # Note: sentence should end with ".", "third person" - https://news.ycombinator.com/item?id=36262670
    # prompt = f'Output only answers to following 3 steps.\n' \
    #          f'1 - Summarize the article delimited by triple backticks in 2 sentences.\n' \
    #          f'2 - Translate the summary into Chinese.\n' \
    #          f'3 - Provide a Chinese translation of sentence: "{title}".\n' \
    #          f'```{content.strip(".")}.```'

    kwargs = {'model': config.openai_model,
              # one token generally corresponds to ~4 characters
              # 'max_tokens': int(config.summary_size / 4),
              'stream': False,
              'temperature': 0,
              'n': 1,  # only one choice
              "frequency_penalty": 1,  # Avoid token repetition
              "presence_penalty": 1,
              'timeout': 30}
    if model_family() == Model.GEMMA:
        # Gemma outputs weird words like Kün/viciss/▁purcha/▁xPos/▁Gorb
        kwargs['logit_bias'] = {200507: -100, 225856: -100, 6204: -100, 232014: -100, 172406: -100}

    logger.warning(f'content: {content}')  # for syslog
    resp = openai.ChatCompletion.create(
        messages=[
            {
                "role": "system",
                "content": sys_prompt
            },
            {'role': 'user', 'content': content},
        ],
        **kwargs)
    logger.warning(f'took {time.time() - start_time}s to generate: '
                   # Default str(resp) prints \u516c
                   f'{json.dumps(resp.to_dict_recursive(), sort_keys=True, indent=2, ensure_ascii=False)}')
    if 'error' in resp:
        raise Exception(f'error message: {resp["error"].get("message")}, code: {resp["error"].get("code")}')
    message = resp["choices"][0]["message"]
    if message.get('function_call'):
        json_str = message['function_call']['arguments']
        if resp["choices"][0]['finish_reason'] == 'length':
            json_str += '"}'  # best effort to save truncated answers
        try:
            answer = json.loads(json_str)
        except JSONDecodeError as e:
            logger.warning(f'Failed to decode answer from openai, will fallback to plain text, error: {e}')
            return ''  # Let fallback code kicks in
    else:
        answer = message['content'].strip()
    if '</think>' in answer:
        # A reasoning model
        answer = answer.split('</think>', 1)[-1].strip()
    # Gemma sometimes returns "**Summary:**\n\nXXX\n\n**Key points:**\n\nXXX", extract the summary part
    for line in answer.split('\n'):
        if not line.strip():
            continue
        if 'summary' in line.lower() and line.strip()[-1] == ':':
            continue
        answer = line
        break
    # Remove leading ': ', ' *-' etc. from answer
    answer = re.sub(r'^[^a-zA-Z0-9]+', '', answer)
    # Always have bold **?
    answer = answer.replace('**', ' ')
    answer = re.sub(r'^summary:?', '', answer, flags=re.IGNORECASE)
    return answer.strip()


def summarize_by_openai_family(content: str) -> str:
    return call_openai_family(content,
                              "You are a helpful summarizer. Please think step by step to summarize all user's input in 2 concise English sentences. Ensure the summary does not exceed 200 "
                              "characters. Provide response in plain text format without any Markdown formatting.")


def translate_by_openai_family(content: str, lang: str) -> str:
    return call_openai_family(content, f"You are a helpful translator. Translate user's input into {lang}.")
