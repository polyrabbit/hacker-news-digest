#coding: utf-8

def word_count(s):
    return len(s.split())

def is_paragraph(s):
    """
    Guess if this string is eligible to be a paragraph
    """
    return len(s) > 120