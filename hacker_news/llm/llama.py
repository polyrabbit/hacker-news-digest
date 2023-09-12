import json
import os

from llama_cpp import Llama

import config

llm = Llama(model_path=config.llama_model, n_ctx=2048, n_threads=os.cpu_count() // 2, use_mmap=True, verbose=False)

summary_instruction = '<<SYS>>Summarize following article in 3 sentences.<</SYS>>\n'


def summarize_by_llama(content: str):
    content = content.strip()
    tokens = llm.tokenize(content.encode('utf8'))
    if len(tokens) > llm.n_ctx():  # avoid ValueError
        tokens = tokens[:llm.n_ctx() - len(llm.tokenize(summary_instruction.encode('utf8')))]
        content = llm.detokenize(tokens).decode('utf8')

    return llm(f'{summary_instruction}{content}', max_tokens=config.summary_size // 4, temperature=1, stream=False)


if __name__ == '__main__':
    fpath = os.path.join(os.path.dirname(__file__), '../../test/fixtures/telnet.txt')
    with open(fpath) as file:
        file_contents = file.read()
    print(json.dumps(summarize_by_llama(file_contents)))
