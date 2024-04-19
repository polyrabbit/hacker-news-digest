import json
import logging
import random
import time

import config
from hacker_news.llm.openai import sanitize_for_openai
from page_content_extractor import session

logger = logging.getLogger(__name__)

coze_headers = {
    'Authorization': f'Bearer {config.coze_api_key}',
}


# example response (SSEs):
# b'event:message
# data:{
#     "messages": [
#         {
#             "role": "assistant",
#             "type": "answer",
#             "content": "Sure, how about this one:\n\n\"Read the following article and provide a concise summary, outlining the main points, key findings, and any conclusions drawn.\"",
#             "content_type": "text"
#         },
#         {
#             "role": "assistant",
#             "type": "follow_up",
#             "content": "What are the main points of the article?",
#             "content_type": "text"
#         },
#         {
#             "role": "assistant",
#             "type": "follow_up",
#             "content": "What were the key findings mentioned in the article?",
#             "content_type": "text"
#         },
#         {
#             "role": "assistant",
#             "type": "follow_up",
#             "content": "Were any conclusions drawn in the article?",
#             "content_type": "text"
#         }
#     ],
#     "conversation_id": "123",
#     "code": 0,
#     "msg": "success"
# }'


def summarize_by_coze(content: str) -> str:
    if not config.coze_enabled():
        return ''

    start_time = time.time()
    # Seems coze adds more context in prompt, and even answer is counted
    content = sanitize_for_openai(content, overhead=1000)

    # For model: GPT-4 Turbo (128K), temperature: 0.5 - GPT-4 Turbo is an excellent rule follower.
    prompt = (f'Use third person mood to summarize the main points of the following article delimited by triple backticks in 2 concise English sentences. '
              f'Ensure the summary does not exceed 300 characters.\n'
              f'```{content}.```')

    try:
        resp = session.post(url=config.coze_api_endpoint,
                            headers=coze_headers,
                            stream=True,
                            timeout=30,
                            json={
                                'conversation_id': f'{random.randint(100, 9999)}',
                                'bot_id': config.coze_bot_id,
                                'user': 'single_user',
                                'query': prompt,
                                'stream': False,
                            })
        resp.raise_for_status()
        resp_json = resp.json()
    except Exception as e:
        logger.warning(f'Failed to summarize using coze, {e}')
        return ''

    if resp_json.get('code', 'not-exist') != 0:
        logger.warning(f'Unexpected coze response, code: {resp_json.get("code", "not-exist")}, msg: {resp_json.get("msg", "not-exist")}')
        return ''

    if len(resp_json.get('messages', [])) == 0:
        logger.warning(f'Unexpected coze response, no message list')
        return ''

    for msg in resp_json['messages']:
        if msg['type'] == 'answer' and msg.get('content'):
            summary = msg['content'].strip()
            if summary.startswith('"') and summary.endswith('"'):
                summary = summary[1:-1]
            logger.info(f'took {time.time() - start_time}s to generate: {summary}')
            return summary.strip()

    logger.warning(f'Unexpected coze response, no answer message found')
    return ''
