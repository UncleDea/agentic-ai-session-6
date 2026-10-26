"""Read one public educational page into article text.

url_safety decides whether an address may be opened.
fetch downloads the page and returns the title, headings, and visible text.
"""

from studymaster.extraction.fetch import Article, read_page

__all__ = ["Article", "read_page"]
