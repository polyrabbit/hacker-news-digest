import json
import logging
import os
import re
import time
from json import JSONDecodeError

import openai
import tiktoken
from slugify import slugify

import config
import db.summary
from db.summary import Model
from page_content_extractor import parser_factory
from page_content_extractor.webimage import WebImage

logger = logging.getLogger(__name__)


class News:

    def __init__(self, rank=-1, title='', url='', comhead='', score='', author='',
                 author_link='', submit_time='', comment_cnt='', comment_url=''):
        self.rank = rank
        self.title = title.strip()
        self.url = url
        self.comhead = comhead
        self.score = score
        self.author = author
        self.author_link = author_link
        self.submit_time = submit_time
        self.comment_cnt = comment_cnt
        self.comment_url = comment_url
        self.summary = ''
        self.summarized_by: Model = Model.FULL
        self.favicon = ''
        self.image = None
        self.img_id = ''
        self.cache: db.Summary = db.Summary(url)

    def __repr__(self):
        return f'{self.rank} - {self.title} - {self.url} - {self.score} - {self.author}- {self.submit_time}'

    def get_image_url(self):
        if self.image and self.image.url:
            return self.image.url
        return ''

    def pull_content(self):
        try:
            self.cache = db.summary.get(self.url)
            if not self.title and hasattr(self.parser, 'title'):
                self.title = self.parser.title.strip()
            if self.cache.favicon:
                self.favicon = self.cache.favicon
            else:
                self.favicon = self.cache.favicon = self.parser.get_favicon_url()
            self.summary, self.summarized_by = self.summarize()
            self.cache.summary, self.cache.model = self.summary, self.summarized_by.value
            self.fetch_feature_image()
        except Exception as e:
            logger.exception('Failed to fetch %s, %s', self.url, e)
        if not self.summary:  # last resort, in case remote server is down
            self.summary, self.summarized_by = self.cache.summary, self.cache.get_summary_model()
        return db.summary.put(self.cache)

    @property
    def parser(self):  # lazy load
        if not hasattr(self, '_parser'):
            logger.info("#%d, fetching %s", self.rank, self.url)
            self._parser = parser_factory(self.url)
        return self._parser

    def get_score(self) -> int:
        if isinstance(self.score, int):
            return self.score
        try:
            return int(self.score.strip())
        except:
            return 0

    def slug(self):
        return slugify(self.title or 'no title')

    def summarize(self, content=None) -> (str, Model):
        # settled summary
        if self.cache.model in (Model.EMBED.value, Model.OPENAI.value):
            logger.info(f"Cache hit for {self.url}, model {self.cache.model}")
            return self.cache.summary, self.cache.get_summary_model()
        if content is None:
            # Replace consecutive spaces with a single space
            content = re.sub(r'\s+', ' ', self.parser.get_content(config.max_content_size))
            # From arxiv or pdf
            content = re.sub(r'^(abstract|summary):\s*', '', content,
                             flags=re.IGNORECASE).strip()
        if content.startswith('<iframe '):
            return content, Model.EMBED
        if len(content) <= config.summary_size:
            if self.cache.summary and self.cache.model != Model.FULL.value:
                logger.info(f'Use cached summary, discarding "{content[:1024]}"')
                return self.cache.summary, self.cache.get_summary_model()
            logger.info(
                f'No need to summarize since we have a small text of size {len(content)}')
            return content, Model.FULL

        summary = self.summarize_by_openai(content)
        if summary:
            return summary, Model.OPENAI
        if self.get_score() >= 10:  # Avoid slow local inference
            if Model.from_value(self.cache.model).local_llm() and self.cache.summary:
                logger.info(f'Cache hit for {self.url}, model {self.cache.model}')
                return self.cache.summary, self.cache.get_summary_model()
            summary = self.summarize_by_llama(content)
            if summary:
                return summary, Model.LLAMA
            summary = self.summarize_by_transformer(content)
            if summary:
                return summary, Model.TRANSFORMER
        else:
            logger.info("Score %d is too small, ignore local llm", self.get_score())
        return content, Model.PREFIX

    def summarize_by_openai(self, content):
        if not openai.api_key:
            logger.info("OpenAI API key is not set")
            return ''
        if self.get_score() < config.openai_score_threshold:  # Avoid expensive openai
            logger.info("Score %d is too small, ignore openai", self.get_score())
            return ''

        content = content.replace('```', ' ').strip()  # in case of prompt injection

        # one token generally corresponds to ~4 characters, from https://platform.openai.com/tokenizer
        if len(content) > 4096 * 2:
            enc = tiktoken.encoding_for_model(config.openai_model)
            tokens = enc.encode(content)
            if len(tokens) > 4096 - 200:  # 4096: model's context limit, 200: function + prompt tokens (to reduce hitting rate limit)
                content = enc.decode(tokens[:4096 - 200])

        title = self.title.replace('"', "'").replace('\n', ' ').strip() or 'no title'
        # Hope one day this model will be clever enough to output correct json
        # Note: sentence should end with ".", "third person" - https://news.ycombinator.com/item?id=36262670
        prompt = f'Output only answers to following 3 steps.\n' \
                 f'1 - Summarize the article delimited by triple backticks in 2 sentences.\n' \
                 f'2 - Translate the summary into Chinese.\n' \
                 f'3 - Provide a Chinese translation of sentence: "{title}".\n' \
                 f'```{content.strip(".")}.```'
        try:
            answer = self.openai_complete(prompt, True)
            summary = self.parse_step_answer(answer).strip()
            if not summary:  # If step parse failed, ignore the translation
                summary = self.openai_complete(
                    f'Summarize the article delimited by triple backticks in 2 sentences.\n'
                    f'```{content.strip(".")}.```', False)
            return summary
        except Exception as e:
            logger.exception(f'Failed to summarize using openai, {e}')  # Make this error explicit in the log
            return ''

    def openai_complete(self, prompt, need_json):
        start_time = time.time()
        kwargs = {'model': config.openai_model,
                  # one token generally corresponds to ~4 characters
                  # 'max_tokens': int(config.summary_size / 4),
                  'stream': False,
                  'temperature': 0,
                  'n': 1,  # only one choice
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
        return answer

    def parse_step_answer(self, answer):
        if not answer:
            return answer
        db.translation.add(answer.get('summary', ''), answer.get('summary_zh', ''), 'zh')
        db.translation.add(self.title, self.parse_title_translation(answer.get('translation', '')), 'zh')
        return answer.get('summary', '')

    def parse_title_translation(self, title):
        # Somehow, openai always return the original title
        title_cn = title.removesuffix('。').removesuffix('.')
        match = re.search(r'^"[^"]+"[^"]+“([^”]+)”', title_cn)
        if match:  # clean path
            return match.group(1).strip()
        match = re.search(r'(.*)\(Note.*\)$', title_cn)
        if match:
            return match.group(1).strip()

        parts = re.split(r'的中文翻译(?:[为是])?(?:：)?', title_cn, maxsplit=1)
        if len(parts) > 1 and parts[1].strip():
            title_cn = parts[1].strip().strip(':').strip('：').strip()
        else:
            title_cn = parts[0].strip()
        quote = ('"', '“', '”', '《', '》')  # they are used interchangeably
        while title_cn and title_cn[0] in quote and title_cn[-1] in quote:
            title_cn = title_cn[1:-1].strip()
        return title_cn.removesuffix('。').removesuffix('.').strip()

    def fetch_feature_image(self):
        if config.force_fetch_feature_image:
            logger.warning(f'Will force fetch feature image')
        elif self.cache.image_name is not None:
            if os.path.exists(os.path.join(config.image_dir, self.cache.image_name)):
                self.image = WebImage.from_json_str(self.cache.image_json)
                self.img_id = self.cache.image_name
                logger.info(f"Cache hit image {self.img_id}")
                return
            else:
                logger.info(f'{self.cache.image_name} not exist in {config.image_dir}')
        tm = self.parser.get_illustration()
        if tm:
            tm.try_compress()
            fname = tm.uniq_name()
            tm.save(os.path.join(config.image_dir, fname))
            self.image = tm
            self.cache.image_json = tm.to_json_str()
            self.img_id = fname
        self.cache.image_name = self.img_id  # tried but not found

    def summarize_by_llama(self, content):
        if config.disable_llama:
            logger.info("LLaMA is disabled by env DISABLE_LLAMA=1")
            return ''

        start_time = time.time()
        from hacker_news.llm.llama import summarize_by_llama
        resp = summarize_by_llama(content)
        logger.info(f'took {time.time() - start_time}s to generate: {resp}')
        return resp['choices'][0]['text'].strip()

    def summarize_by_transformer(self, content):
        if config.disable_transformer:
            logger.warning("Transformer is disabled by env DISABLE_TRANSFORMER=1")
            return ''

        start_time = time.time()
        # Too time-consuming to init t5 model, so lazy load here until we have to
        from hacker_news.llm.google_t5 import summarize_by_t5
        summary = summarize_by_t5(content)
        logger.info(f'took {time.time() - start_time}s to generate: {summary}')
        return summary
