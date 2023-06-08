import logging
import os
import re
import time
from enum import Enum

import openai
from summarizer import Summarizer
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

import config
from hacker_news import summary_cache, translation
from page_content_extractor import parser_factory

logger = logging.getLogger(__name__)

# google t5 transformer
model, tokenizer, bert_model = None, None, None
if not config.disable_transformer:
    MAX_TOKEN = 4096
    # github runner only has 7 GB of RAM, https://docs.github.com/en/actions/using-github-hosted-runners/about-github-hosted-runners
    MODEL_NAME = config.transformer_model
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, model_max_length=MAX_TOKEN)
    bert_model = Summarizer()


class SummaryModel(Enum):
    PREFIX = 'Prefix'
    FULL = 'Full'
    EMBED = 'Embed'
    OPENAI = 'OpenAI'
    TRANSFORMER = 'GoogleT5'


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
        self.content = ''
        self.summary = ''
        self.summarized_by = SummaryModel.FULL
        self.favicon = ''
        self.image = None
        self.img_id = None

    def get_image_url(self):
        if self.image and self.image.url:
            return self.image.url
        return ''

    def pull_content(self):
        try:
            logger.info("#%d, fetching %s", self.rank, self.url)
            parser = parser_factory(self.url)
            self.favicon = parser.get_favicon_url()
            # Replace consecutive spaces with a single space
            self.content = re.sub(r'\s+', ' ', parser.get_content(config.max_content_size))
            self.summary = self.summarize()
            tm = parser.get_illustration()
            if tm:
                fname = tm.uniq_name()
                tm.save(os.path.join(config.output_dir, "image", fname))
                self.image = tm
                self.img_id = fname
        except Exception as e:
            logger.exception('Failed to fetch %s, %s', self.url, e)
        if not self.summary:  # last resort, in case remote server is down
            self.summary = summary_cache.get(self.url)

    def get_score(self):
        try:
            return int(self.score.strip())
        except:
            return 0

    def summarize(self):
        if not self.content:
            return ''
        if self.content.startswith('<iframe '):
            self.summarized_by = SummaryModel.EMBED
            return self.content
        if len(self.content) <= config.summary_size:
            logger.info(
                f'No need to summarize since we have a small text of size {len(self.content)}')
            return self.content

        summary = self.summarize_by_openai(self.content.strip())
        if summary:
            self.summarized_by = SummaryModel.OPENAI
            return summary
        summary = self.summarize_by_transformer(self.content.strip())
        if summary:
            self.summarized_by = SummaryModel.TRANSFORMER
            return summary
        else:
            self.summarized_by = SummaryModel.PREFIX
            return self.content

    def summarize_by_openai(self, content):
        summary = summary_cache.get(self.url, SummaryModel.OPENAI)
        if summary:
            logger.info("Cache hit for %s", self.url)
            return summary
        if not openai.api_key:
            logger.info("OpenAI API key is not set")
            return ''
        if self.get_score() <= config.openai_score_threshold:  # Avoid expensive openai
            logger.info("Score %d is too small, ignore openai", self.get_score())
            return ''

        if len(content) > 4096 * 2:
            # one token generally corresponds to ~4 characters, from https://platform.openai.com/tokenizer
            content = content[:4096 * 2]

        content = content.replace('```', ' ').strip()  # in case of prompt injection
        title = self.title.replace('"', "'").strip() or 'no title'
        start_time = time.time()
        prompt = f'Output only answers to following steps, prefix each answer with step number.\n' \
                 f'1 - Summarize the article delimited by triple backticks in 2 sentences.\n' \
                 f'2 - Translate the summary into Chinese.\n' \
                 f'3 - Output only Chinese translation of text: "{title}".\n' \
                 f'```{content}```'
        kwargs = {'model': config.openai_model,
                  # one token generally corresponds to ~4 characters
                  # 'max_tokens': int(config.summary_size / 4),
                  'stream': False,
                  'temperature': 0,
                  'n': 1,  # only one choice
                  'timeout': 30}
        try:
            resp = openai.ChatCompletion.create(
                messages=[
                    {'role': 'user', 'content': prompt},
                ],
                **kwargs)
            answer = resp['choices'][0]['message']['content'].strip()
            logger.info(f'took {time.time() - start_time}s to generate: {resp}')
            lines = re.split(r'\n+', answer)
            # Hard to tolerate all kinds of formats, so just handle one
            pattern = r'^(\d+)\s*-\s*'
            for i, line in enumerate(lines):
                match = re.match(pattern, line)
                if not match:
                    logger.warning(f'Answer line: {line} has no step number')
                    return ''
                if str(i + 1) != match.group(1):
                    logger.warning(f'Answer line {line} does not match step: {i + 1}')
                    return ''
                lines[i] = re.sub(pattern, '', line)
            if len(lines) < 3:
                return lines[0]  # only get the summary
            translation.add(lines[0], lines[1], 'zh')
            # Somehow, openai always return the original title
            title_cn = lines[2].removesuffix('。').removesuffix('.')
            parts = re.split(r'的中文翻译(?:为)?', title_cn, maxsplit=1)
            if len(parts) > 1 and parts[1].strip():
                title_cn = parts[1].strip().strip(':').strip('：')
            else:
                title_cn = parts[0].strip()
            translation.add(self.title, title_cn.strip('"').strip('“'), 'zh')
            return lines[0]
        except Exception as e:
            logger.warning('Failed to summarize using openai, %s', e)
            return ''

    def summarize_by_transformer(self, content):
        if config.disable_transformer:
            logger.warning("Transformer is disabled by env DISABLE_TRANSFORMER=1")
            return ''
        summary = summary_cache.get(self.url, SummaryModel.TRANSFORMER)
        if summary:
            logger.info("Cache hit for %s", self.url)
            return summary
        if self.get_score() <= 10:  # Avoid slow transformer
            logger.info("Score %d is too small, ignore transformer", self.get_score())
            return ''

        start_time = time.time()
        if len(content) > tokenizer.model_max_length:
            content = bert_model(content, use_first=True,
                                 ratio=tokenizer.model_max_length / len(content))
        tokens_input = tokenizer.encode("summarize: " + content, return_tensors='pt',
                                        max_length=tokenizer.model_max_length,
                                        truncation=True)
        summary_ids = model.generate(tokens_input, min_length=80,
                                     max_length=int(config.summary_size / 4),  # tokens
                                     length_penalty=20,
                                     no_repeat_ngram_size=2,
                                     temperature=0,
                                     num_beams=2)
        summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True,
                                   clean_up_tokenization_spaces=True).capitalize()
        logger.info(f'took {time.time() - start_time}s to generate: {summary}')
        return summary
