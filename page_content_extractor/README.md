This internal package provides a unified way to extract main body from `html` and `pdf`.

### Usage

Feed a url to the `parser_factory` and you will get a page object

 ```
 page = parser_factory('https://github.com/polyrabbit/hacker-news-digest')
 ```

From the page you can get the main body via the `aritcle` attribute, the summary of body via the `get_summary` method, the illustration via the `get_illustration` method, and the favicon url via the `get_favicon_url` method.

```
>>> page.article
lots of html stuff

>>> page.get_summary(max_length=100)
u'This service extracts summaries and images from  hacker newsarticles for people who want to get the  ...'

>>> page.get_illustration()
<page_content_extractor.html.WebImage at 0x10bc28cd0>

>>> page.get_favicon_url()
'https://github.com/fluidicon.png'
```