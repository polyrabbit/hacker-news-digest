import logging

from summarizer import Summarizer
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

import config

logger = logging.getLogger(__name__)

# google t5 transformer
MAX_TOKEN = 4096
# github runner only has 7 GB of RAM, https://docs.github.com/en/actions/using-github-hosted-runners/about-github-hosted-runners
MODEL_NAME = config.transformer_model
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, model_max_length=MAX_TOKEN)
bert_model = Summarizer()


def summarize_by_t5(content):
    if len(content) > tokenizer.model_max_length:
        content = bert_model(content, use_first=True,
                             ratio=tokenizer.model_max_length / len(content))
    tokens_input = tokenizer.encode("summarize: " + content, return_tensors='pt',
                                    max_length=tokenizer.model_max_length,
                                    truncation=True)
    summary_ids = model.generate(tokens_input, min_length=80,
                                 max_length=config.summary_size // 4,  # tokens
                                 length_penalty=20,
                                 no_repeat_ngram_size=2,
                                 temperature=0,
                                 num_beams=2)
    return tokenizer.decode(summary_ids[0], skip_special_tokens=True,
                            clean_up_tokenization_spaces=True).capitalize()
