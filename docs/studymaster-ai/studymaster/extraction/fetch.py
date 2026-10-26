"""Download one public page and return its article text.

Redirects are followed one hop at a time. Each hop is checked before connecting.
A failed read raises a reader error and does not invent replacement text.
"""

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from studymaster.config import Settings, get_settings
from studymaster.extraction.errors import (
    FetchError,
    ReaderError,
    ResponseTooLargeError,
    UnreadablePageError,
    UnsupportedContentError,
)
from studymaster.extraction.url_safety import Resolver, assert_safe_url

logger = logging.getLogger(__name__)

_USER_AGENT = "StudyMasterAI/0.1 educational page reader"
_REDIRECT_STATUSES = {301, 302, 303, 307, 308}
_MAX_REDIRECTS = 5
_HTML_TYPES = {"text/html", "application/xhtml+xml"}
_TEXT_TYPE = "text/plain"


@dataclass(frozen=True)
class Article:
    """Text extracted from one page."""

    url: str
    title: str
    headings: list[str]
    text: str
    shortened: bool


class PageResponse(Protocol):
    """The small part of an HTTP response this reader uses."""

    status_code: int
    headers: dict[str, str]
    url: str

    def iter_content(self, chunk_size: int) -> Iterator[bytes]:
        """Yield the next piece of the decoded body."""

    def close(self) -> None:
        """Release the connection."""


class Transport(Protocol):
    """Downloads one address without following redirects."""

    def get(
        self,
        url: str,
        *,
        timeout: float,
        headers: dict[str, str],
    ) -> PageResponse:
        """Return the response for one request."""


class RequestsTransport:
    """Download with the requests library. Redirects stay off."""

    def get(
        self,
        url: str,
        *,
        timeout: float,
        headers: dict[str, str],
    ) -> PageResponse:
        return requests.get(
            url,
            timeout=timeout,
            headers=headers,
            allow_redirects=False,
            stream=True,
        )


def read_page(
    url: str,
    *,
    settings: Settings | None = None,
    transport: Transport | None = None,
    resolve: Resolver | None = None,
) -> Article:
    """Read one page and return its article.

    settings, transport, and resolve have defaults. Tests replace them so
    no test calls the public internet.
    """
    active_settings = settings or get_settings()
    active_transport = transport or RequestsTransport()
    current = url
    try:
        for hop in range(_MAX_REDIRECTS + 1):
            assert_safe_url(current, resolve=resolve)
            response = _open(active_transport, current, active_settings)
            try:
                if response.status_code in _REDIRECT_STATUSES:
                    if hop == _MAX_REDIRECTS:
                        raise FetchError("The page redirected too many times.")
                    current = _next_url(current, response.headers)
                    continue
                if response.status_code < 200 or response.status_code >= 300:
                    raise FetchError("The page could not be downloaded.")
                content_type = _header(response.headers, "Content-Type")
                body = _read_limited(response, active_settings.max_response_bytes)
            finally:
                response.close()
            article = _article_from_body(
                current,
                body,
                content_type,
                active_settings,
            )
            logger.info(
                "Page read host=%s shortened=%s",
                _host_for_log(current),
                article.shortened,
            )
            return article
    except ReaderError as exc:
        logger.warning(
            "Page read failed host=%s error=%s",
            _host_for_log(current),
            type(exc).__name__,
        )
        raise
    raise FetchError("The page redirected too many times.")


def _open(transport: Transport, url: str, settings: Settings) -> PageResponse:
    headers = {
        "User-Agent": _USER_AGENT,
        "Accept": "text/html, text/plain;q=0.9",
    }
    try:
        return transport.get(url, timeout=settings.fetch_timeout_seconds, headers=headers)
    except requests.RequestException as exc:
        raise FetchError("The page could not be downloaded.") from exc


def _next_url(current: str, headers: dict[str, str]) -> str:
    location = _header(headers, "Location")
    if not location:
        raise FetchError("The page could not be downloaded.")
    return urljoin(current, location)


def _read_limited(response: PageResponse, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_content(chunk_size=8192):
        if not chunk:
            continue
        total += len(chunk)
        if total > max_bytes:
            raise ResponseTooLargeError("This page is too large to read.")
        chunks.append(chunk)
    return b"".join(chunks)


def _article_from_body(
    url: str,
    body: bytes,
    content_type: str,
    settings: Settings,
) -> Article:
    kind = _content_kind(content_type)
    page_text = _decode(body, content_type)
    host = _host_for_log(url)
    if kind == "text":
        title = host or "Untitled page"
        headings: list[str] = []
        text = _collapse(page_text)
    else:
        title, headings, text = _html_article(page_text, host)
    if len(text) < settings.min_source_chars:
        raise UnreadablePageError("This page did not include readable article text.")
    shortened = len(text) > settings.max_source_chars
    if shortened:
        text = text[: settings.max_source_chars]
    return Article(
        url=url,
        title=title,
        headings=headings,
        text=text,
        shortened=shortened,
    )


def _html_article(page_text: str, host: str) -> tuple[str, list[str], str]:
    soup = BeautifulSoup(page_text, "html.parser")
    document_title = ""
    if soup.title:
        document_title = _collapse(soup.title.get_text(" ", strip=True))
    for tag in soup.find_all(["script", "style", "nav", "header", "footer", "aside", "form"]):
        tag.decompose()
    region = soup.find("main") or soup.find("article") or soup.body or soup
    headings = [
        _collapse(heading.get_text(" ", strip=True))
        for heading in region.find_all(["h1", "h2", "h3"])
    ]
    headings = [heading for heading in headings if heading]
    title = document_title or (headings[0] if headings else "") or host or "Untitled page"
    text = _collapse(region.get_text("\n", strip=True))
    return title, headings, text


def _content_kind(content_type: str) -> str:
    media = content_type.split(";", 1)[0].strip().lower()
    if media in _HTML_TYPES:
        return "html"
    if media == _TEXT_TYPE:
        return "text"
    raise UnsupportedContentError("This page is not a readable article.")


def _decode(body: bytes, content_type: str) -> str:
    charset = "utf-8"
    for part in content_type.split(";")[1:]:
        name, separator, value = part.strip().partition("=")
        if separator and name.lower() == "charset" and value:
            charset = value.strip().strip('"')
    try:
        return body.decode(charset, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


def _collapse(text: str) -> str:
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _header(headers: dict[str, str], name: str) -> str:
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value.strip()
    return ""


def _host_for_log(url: str) -> str:
    host = urlparse(url).hostname
    if not host:
        return "unknown"
    return host.lower()
