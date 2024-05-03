import json
import logging
import re
import time
from json import JSONDecodeError

import openai
import tiktoken
import config

logger = logging.getLogger(__name__)


def context_limit(model: str):
    if '128k' in model:
        return 128 * 1024
    if '32k' in model or 'mistral-7b' in model:
        return 32 * 1024
    if 'gemma-7b' in model:
        return 8 * 1024
    return 4096


def sanitize_for_openai(text, overhead):
    text = text.replace('```', ' ').strip()  # in case of prompt injection

    limit = context_limit(config.openai_model)
    # one token generally corresponds to ~4 characters, from https://platform.openai.com/tokenizer
    if len(text) > limit * 2:
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


def summarize_by_openai_family(content: str, need_json: bool):
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

    prompt = (f'Use third person mood to summarize the following article delimited by triple backticks in 2 concise English sentences. Ensure the summary does not exceed 100 characters.\n'
              f'```{content.strip(".")}.```')

    kwargs = {'model': config.openai_model,
              # one token generally corresponds to ~4 characters
              # 'max_tokens': int(config.summary_size / 4),
              'stream': False,
              'temperature': 0,
              'n': 1,  # only one choice
              "frequency_penalty": 1,  # Avoid token repetition
              "presence_penalty": 1,
              'timeout': 30}
    if need_json:
        kwargs['functions'] = [{"name": "render", "parameters": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "English summary"
                },
                "summary_zh": {
                    "type": "string",
                    "description": "Chinese summary"
                },
                "translation": {
                    "type": "string",
                    "description": "Chinese translation of sentence"
                },
            },
            # "required": ["summary"]  # ChatGPT only returns the required field?
        }}]
        kwargs['function_call'] = {"name": "render"}

    if config.openai_model.startswith('text-'):
        resp = openai.Completion.create(
            prompt=prompt,
            **kwargs
        )
        answer = resp['choices'][0]['text'].strip()
    else:
        resp = openai.ChatCompletion.create(
            messages=[
                {'role': 'user', 'content': prompt},
            ],
            **kwargs)
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
    logger.info(f'prompt: {prompt}')
    logger.info(f'took {time.time() - start_time}s to generate: '
                # Default str(resp) prints \u516c
                f'{json.dumps(resp.to_dict_recursive(), sort_keys=True, indent=2, ensure_ascii=False)}')
    # Remove leading ': ', ' *-' etc. from answer
    answer = answer.strip('**Summary:**')
    answer = re.sub(r'^[^a-zA-Z0-9]+', '', answer)
    return answer.strip()
