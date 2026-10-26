"""Find one public https address when the starter list has no match.

The search page is read only to copy one address. That address is checked
and then shown. It is not opened.
"""

import logging
from collections.abc import Callable
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from bs4 import BeautifulSoup

from studymaster.extraction.errors import UnsafeUrlError
from studymaster.extraction.url_safety import Resolver, assert_safe_url

logger = logging.getLogger(__name__)

NO_PUBLIC_PAGE = "No public page was found."
USE_PAGE_HINT = "One public page is ready. Press Use this page, then Study this page."

_SEARCH_PAGE = "https://html.duckduckgo.com/html/"
_USER_AGENT = "StudyMasterAI/0.1 educational page reader"
_MAX_CANDIDATES = 8
_MAX_QUERY_CHARS = 200
_MAX_SEARCH_BYTES = 500_000

Fetch = Callable[[str], str]


def find_public_page(
    query: str,
    *,
    fetch: Fetch | None = None,
    resolve: Resolver | None = None,
    timeout: float = 10,
) -> str | None:
    """Return one safe https address, or None when the search has no page.

    fetch and resolve have defaults. Tests replace them so no test calls the
    public internet.
    """
    needle = " ".join(query.split())[:_MAX_QUERY_CHARS]
    if not needle:
        return None
    search_url = f"{_SEARCH_PAGE}?{urlencode({'q': needle})}"
    try:
        html = _read_search(search_url, fetch=fetch, resolve=resolve, timeout=timeout)
        for address in _candidate_urls(html):
            try:
                assert_safe_url(address, resolve=resolve)
            except UnsafeUrlError:
                continue
            logger.info("Public page offered host=%s", urlparse(address).hostname)
            return address
    except (requests.RequestException, OSError, UnsafeUrlError):
        logger.info("Public page search failed")
        return None
    logger.info("Public page search found nothing")
    return None


def _read_search(
    url: str,
    *,
    fetch: Fetch | None,
    resolve: Resolver | None,
    timeout: float,
) -> str:
    if fetch is not None:
        return fetch(url)
    assert_safe_url(url, resolve=resolve)
    response = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": _USER_AGENT},
        allow_redirects=False,
        stream=True,
    )
    try:
        if response.status_code != 200:
            return ""
        pieces: list[bytes] = []
        size = 0
        for chunk in response.iter_content(chunk_size=8192):
            if not chunk:
                continue
            size += len(chunk)
            if size > _MAX_SEARCH_BYTES:
                break
            pieces.append(chunk)
        return b"".join(pieces).decode("utf-8", errors="replace")
    finally:
        response.close()


def _candidate_urls(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    anchors = soup.select("a.result__a")
    if not anchors:
        anchors = soup.find_all("a", href=True)
    found: list[str] = []
    for anchor in anchors:
        address = _result_url(str(anchor.get("href", "")))
        if address and address not in found:
            found.append(address)
        if len(found) >= _MAX_CANDIDATES:
            break
    return found


def _result_url(href: str) -> str | None:
    href = href.strip()
    if href.startswith("//"):
        href = f"https:{href}"
    parsed = urlparse(href)
    uddg = parse_qs(parsed.query).get("uddg", [])
    target = uddg[0] if uddg else href
    parsed_target = urlparse(target)
    if parsed_target.scheme != "https" or not parsed_target.hostname:
        return None
    host = parsed_target.hostname.lower().rstrip(".")
    if host == "duckduckgo.com" or host.endswith(".duckduckgo.com"):
        return None
    return target.split("#", 1)[0]
