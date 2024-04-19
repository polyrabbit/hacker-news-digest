import logging

import requests
import requests.utils
import urllib3
from fake_useragent import UserAgent
from requests.adapters import HTTPAdapter
from urllib3.util import timeout
from urllib3.util.ssl_ import create_urllib3_context

logger = logging.getLogger(__name__)


class CustomHTTPAdapter(HTTPAdapter):
    timeout = timeout.Timeout(connect=10, read=30)

    def __init__(self, *args, **kwargs):
        if "max_retries" not in kwargs:
            # Just fail fast, otherwise the total timeout will be 30s * max_retries
            # bad case is https://struct.ai/blog/introducing-the-struct-chat-platform,
            # which blocks all image requests, so the whole update-round times out
            kwargs['max_retries'] = 1
        # Remove until switching to Python 3.12,
        # https://stackoverflow.com/questions/71603314/ssl-error-unsafe-legacy-renegotiation-disabled
        # https://github.com/urllib3/urllib3/issues/2653
        self.ssl_context = create_urllib3_context()
        self.ssl_context.load_default_certs()
        self.ssl_context.check_hostname = False
        self.ssl_context.options |= 0x4  # OP_LEGACY_SERVER_CONNECT
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        user_time = kwargs.get("timeout")
        if user_time is None:
            kwargs["timeout"] = self.timeout
        return super().send(request, **kwargs)

    def build_response(self, req, resp):
        """Get encoding from html content instead of setting it blindly to ISO-8859-1"""
        response = super().build_response(req, resp)
        if response.encoding == 'ISO-8859-1':
            response.encoding = (requests.utils.get_encodings_from_content(str(response.content))
                                 or ['ISO-8859-1'])[-1]  # the last one overwrites the first one
        # If response.encoding is None, encoding will be guessed using `chardet` by `requests`
        return response

    def init_poolmanager(self, *args, **kwargs):
        kwargs['ssl_context'] = self.ssl_context
        return super().init_poolmanager(*args, **kwargs)


logging.getLogger("requests").setLevel(logging.WARNING)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Some sites just refuses bot connection
ua = UserAgent(browsers=['chrome'], min_percentage=10.0)
ua_str = ua.random
logger.info(f'Use user-agent {ua_str}')

session = requests.Session()

session.mount('http://', CustomHTTPAdapter())
session.mount('https://', CustomHTTPAdapter())

session.headers.update({"User-Agent": ua_str})
session.verify = False
