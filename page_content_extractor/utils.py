#coding: utf-8
import re
import requests
from backports.functools_lru_cache import lru_cache

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

@lru_cache(maxsize=32)
def tokenize(s):  # not using yield just for cache
    """
    >>> tokenize(u'ab我的 wtf ggにほんご ニ')
    (u'ab ', u'我', u'的', u'wtf ', u'gg ', u'に', u'ほ', u'ん', u'ご', u'ニ')

    """
    tokens = []
    for t in ascii_patt.split(s.strip()):
        if t:
            if ascii_patt.match(t):
                tokens.extend([tt+' ' for tt in t.split()])
            else:
                tokens.extend(list(t))
    return tuple(tokens)  # sorry but list is unhashable

def my_default_user_agent(name="python-requests"):
    return "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_0) AppleWebKit/537.36 " \
           "(KHTML, like Gecko) Chrome/45.0.2454.101 Safari/537.36"

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
    kwargs['timeout'] = kwargs['timeout'] or 40
    return origin_send(*args, **kwargs)

def monkey_patch_requests():
    # A monkey patch to impersonate my chrome
    requests.utils.default_user_agent = my_default_user_agent
    requests.adapters.HTTPAdapter.build_response = my_build_response
    requests.adapters.HTTPAdapter.send = send_with_default_args

@lru_cache(maxsize=128)
def LCS_length(x, y):
    """
    Return the length of longest common subsequence of *iterable* x and y
    """
    len_x, len_y = len(x)+1, len(y)+1
    lcs = [[0] for i in range(len_x)]
    lcs[0] = [0 for j in range(len_y)]
    for i in range(1, len_x):
        for j in range(1, len_y):
            lcs[i].append(lcs[i-1][j-1] + 1 if x[i-1]==y[j-1] else
                    max(lcs[i-1][j], lcs[i][j-1]))
    return lcs[len_x-1][len_y-1]

@lru_cache(maxsize=128)
def string_inclusion_ratio(needle, haystack):
    """A naive way to calc to what extent string b contains string a"""
    if not needle.strip() or not haystack.strip():
        return 0
    return LCS_length(tokenize(needle), tokenize(haystack)) / float(len(tokenize(needle)))

