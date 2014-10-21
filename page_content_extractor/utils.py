#coding: utf-8
import re
import requests

# def word_count(s):
#     return len(list(jieba.cut(s)))

def is_paragraph(s):
    """
    Guess if this string is eligible to be a paragraph
    """
    try:
        # Favour CJK words
        return len(s.encode('utf-8')) > 120
    except UnicodeEncodeError:
        return len(s) > 120

ascii_patt = re.compile(ur'([\u0000-\u00FF]+)', re.U)

def tokenize(s):
    tokens = []
    for t in ascii_patt.split(s.strip()):
        if t:
            if ascii_patt.match(t):
                tokens.extend([tt+' ' for tt in t.split()])
            else:
                tokens.extend(list(t))
    return tokens

def my_default_user_agent(name="python-requests"):
    return "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_0) AppleWebKit/537.36 " \
           "(KHTML, like Gecko) Chrome/38.0.2125.101 Safari/537.36"

origin_build_response = requests.adapters.HTTPAdapter.build_response.im_func

def my_build_response(self, req, resp):
    """Get encoding from html content instead of setting it blindly to ISO-8859-1"""
    r = origin_build_response(self, req, resp)
    if r.encoding == 'ISO-8859-1':
        r.encoding = (requests.utils.get_encodings_from_content(r.content) \
                    or ['ISO-8859-1'])[-1]  # the last one overwrites the first one
    return r

origin_send = requests.adapters.HTTPAdapter.send.im_func

def send_with_default_args(*args, **kwargs):
    kwargs['verify'] = False
    kwargs['timeout'] = kwargs['timeout'] or 20
    return origin_send(*args, **kwargs)

def monkey_patch_requests():
    # A monkey patch to impersonate my chrome
    requests.utils.default_user_agent = my_default_user_agent
    requests.adapters.HTTPAdapter.build_response = my_build_response
    requests.adapters.HTTPAdapter.send = send_with_default_args

