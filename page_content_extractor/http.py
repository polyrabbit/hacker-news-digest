import logging

import requests
import requests.utils
import urllib3
from fake_useragent import UserAgent
from requests.adapters import HTTPAdapter
from urllib3.exceptions import InsecureRequestWarning
from urllib3.util import timeout

logger = logging.getLogger(__name__)


class CustomHTTPAdapter(HTTPAdapter):
    timeout = timeout.Timeout(connect=2, read=20)

    def __init__(self, *args, **kwargs):
        if "max_retries" not in kwargs:
            kwargs['max_retries'] = 3
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


logging.getLogger("requests").setLevel(logging.WARNING)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Some sites just refuses bot connection
ua = UserAgent(use_external_data=True, browsers=['chrome'], fallback='Twitterbot/1.0')
ua_str = ua.data_browsers['chrome'][0]  # Use the latest, in case of "unsupported browser" error
logger.info(f'Use user-agent {ua_str}')

session = requests.Session()

session.mount('http://', CustomHTTPAdapter())
session.mount('https://', CustomHTTPAdapter())

session.headers.update({"User-Agent": ua_str})
session.verify = False
