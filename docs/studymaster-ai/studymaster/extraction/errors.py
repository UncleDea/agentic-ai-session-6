"""Errors a learner can be shown when a page cannot be read.

Each message is safe to display. None of them includes a query string.
"""


class ReaderError(Exception):
    """A page could not be turned into article text."""


class UnsafeUrlError(ReaderError):
    """The address is not a public http or https page."""


class FetchError(ReaderError):
    """The download failed, timed out, or redirected too many times."""


class UnsupportedContentError(ReaderError):
    """The response is not HTML or plain text."""


class ResponseTooLargeError(ReaderError):
    """The decoded page is larger than the allowed size."""


class UnreadablePageError(ReaderError):
    """The page downloaded, but it did not contain enough article text."""
