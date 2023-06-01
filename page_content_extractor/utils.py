# coding: utf-8
import re
from functools import lru_cache

ascii_patt = re.compile(r'([\u0000-\u00FF]+)', re.U)


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
                tokens.extend([tt + ' ' for tt in t.split()])
            else:
                tokens.extend(list(t))
    return tuple(tokens)  # sorry but list is unhashable


@lru_cache(maxsize=128)
def LCS_length(x, y):
    """
    Return length of the longest common subsequence of *iterable* x and y
    """
    len_x, len_y = len(x) + 1, len(y) + 1
    lcs = [[0] for i in range(len_x)]
    lcs[0] = [0 for j in range(len_y)]
    for i in range(1, len_x):
        for j in range(1, len_y):
            lcs[i].append(lcs[i - 1][j - 1] + 1 if x[i - 1] == y[j - 1] else
                          max(lcs[i - 1][j], lcs[i][j - 1]))
    return lcs[len_x - 1][len_y - 1]


@lru_cache(maxsize=128)
def string_inclusion_ratio(needle, haystack):
    """A naive way to calc to what extent string b contains string a"""
    if not needle.strip() or not haystack.strip():
        return 0
    return LCS_length(tokenize(needle), tokenize(haystack)) / float(len(tokenize(needle)))
