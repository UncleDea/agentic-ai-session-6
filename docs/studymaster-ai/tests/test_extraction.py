"""Tests for safe page reading.

These tests use fake responses and local HTML files. They do not call the
public internet.
"""

import logging
from pathlib import Path

import pytest
import requests

from studymaster.config import Settings
from studymaster.extraction.errors import (
    FetchError,
    ResponseTooLargeError,
    UnreadablePageError,
    UnsafeUrlError,
    UnsupportedContentError,
)
from studymaster.extraction.fetch import read_page
from studymaster.extraction.url_safety import assert_safe_url

FIXTURES = Path(__file__).parent / "fixtures"
PUBLIC_IP = "93.184.216.34"
HIDDEN_TOKENS = (
    "NAV_ONLY_TOKEN",
    "HEADER_ONLY_TOKEN",
    "ARTICLE_ONLY_TOKEN",
    "ASIDE_ONLY_TOKEN",
    "FOOTER_ONLY_TOKEN",
    "FORM_ONLY_TOKEN",
    "SCRIPT_ONLY_TOKEN",
    "STYLE_ONLY_TOKEN",
)


def settings(**overrides: object) -> Settings:
    """Build settings with known limits so a local .env cannot change the test."""
    values: dict[str, object] = {
        "openai_api_key": None,
        "openai_model": "gpt-4o-mini",
        "fetch_timeout_seconds": 10,
        "max_response_bytes": 1_000_000,
        "max_source_chars": 20_000,
        "min_source_chars": 400,
        "database_path": Path("data/studymaster.db"),
        "openai_timeout_seconds": 60,
        "openai_temperature": 0.2,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def public_resolve(_host: str) -> list[str]:
    """Pretend every host name points at one public address."""
    return [PUBLIC_IP]


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


class FakeResponse:
    """A small stand-in for a streamed HTTP response."""

    def __init__(
        self,
        *,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        body: bytes = b"",
        url: str = "",
        chunk_size: int = 8192,
    ) -> None:
        self.status_code = status_code
        self.headers = headers or {}
        self.url = url
        self._body = body
        self._chunk_size = chunk_size
        self.closed = False

    def iter_content(self, chunk_size: int = 8192):
        step = self._chunk_size or chunk_size
        for start in range(0, len(self._body), step):
            yield self._body[start : start + step]

    def close(self) -> None:
        self.closed = True


class FakeTransport:
    """Returns scripted responses and records every request."""

    def __init__(self, routes: dict[str, FakeResponse]) -> None:
        self.routes = routes
        self.calls: list[str] = []
        self.headers: list[dict[str, str]] = []
        self.timeouts: list[float] = []

    def get(self, url: str, *, timeout: float, headers: dict[str, str]) -> FakeResponse:
        self.calls.append(url)
        self.headers.append(headers)
        self.timeouts.append(timeout)
        if url not in self.routes:
            raise AssertionError(f"unexpected request for {url}")
        return self.routes[url]


def html_response(url: str, body: bytes) -> FakeResponse:
    return FakeResponse(
        headers={"Content-Type": "text/html; charset=utf-8"},
        body=body,
        url=url,
    )


def test_loopback_address_is_rejected() -> None:
    with pytest.raises(UnsafeUrlError):
        assert_safe_url("http://127.0.0.1/")


def test_metadata_address_is_rejected() -> None:
    with pytest.raises(UnsafeUrlError):
        assert_safe_url("http://169.254.169.254/")


def test_decimal_loopback_address_is_rejected() -> None:
    with pytest.raises(UnsafeUrlError):
        assert_safe_url("http://2130706433/")


def test_address_with_password_is_rejected() -> None:
    with pytest.raises(UnsafeUrlError):
        assert_safe_url("http://user:secret@example.com/lesson")


def test_non_http_schemes_are_rejected() -> None:
    with pytest.raises(UnsafeUrlError):
        assert_safe_url("file:///C:/lesson.html")
    with pytest.raises(UnsafeUrlError):
        assert_safe_url("ftp://example.com/lesson")


def test_public_name_pointing_at_a_private_address_is_rejected() -> None:
    def resolve(_host: str) -> list[str]:
        return ["10.1.2.3"]

    transport = FakeTransport({})
    with pytest.raises(UnsafeUrlError):
        read_page(
            "http://example.com/lesson",
            settings=settings(),
            transport=transport,
            resolve=resolve,
        )
    assert transport.calls == []


def test_redirect_to_a_private_address_is_rejected() -> None:
    start = "http://example.com/start"
    transport = FakeTransport(
        {
            start: FakeResponse(
                status_code=302,
                headers={"Location": "http://127.0.0.1/secret"},
                url=start,
            )
        }
    )

    with pytest.raises(UnsafeUrlError):
        read_page(
            start,
            settings=settings(),
            transport=transport,
            resolve=public_resolve,
        )

    assert transport.calls == [start]


def test_oversized_body_is_rejected() -> None:
    url = "http://example.com/huge"
    response = FakeResponse(
        headers={"Content-Type": "text/plain"},
        body=b"x" * 100,
        url=url,
        chunk_size=10,
    )
    transport = FakeTransport({url: response})

    with pytest.raises(ResponseTooLargeError, match="too large"):
        read_page(
            url,
            settings=settings(max_response_bytes=25),
            transport=transport,
            resolve=public_resolve,
        )

    assert response.closed


def test_short_page_returns_no_article_text() -> None:
    url = "http://example.com/short"
    transport = FakeTransport({url: html_response(url, fixture("short_page.html"))})

    with pytest.raises(
        UnreadablePageError,
        match="This page did not include readable article text.",
    ):
        read_page(
            url,
            settings=settings(),
            transport=transport,
            resolve=public_resolve,
        )


def test_simple_html_page_returns_title_heading_and_paragraph() -> None:
    url = "http://example.com/plants"
    transport = FakeTransport({url: html_response(url, fixture("simple_article.html"))})

    article = read_page(
        url,
        settings=settings(),
        transport=transport,
        resolve=public_resolve,
    )

    assert article.url == url
    assert article.title == "Photosynthesis"
    assert article.headings == ["How plants make food"]
    assert "Plants make food from sunlight" in article.text
    assert article.shortened is False


def test_navigation_and_script_text_are_left_out() -> None:
    url = "http://example.com/plants"
    transport = FakeTransport({url: html_response(url, fixture("nav_and_script.html"))})

    article = read_page(
        url,
        settings=settings(),
        transport=transport,
        resolve=public_resolve,
    )

    assert article.headings == ["How plants make food", "Leaves and light"]
    assert "MAIN_ONLY_TOKEN" in article.text
    for token in HIDDEN_TOKENS:
        assert token not in article.text
        assert token not in " ".join(article.headings)


def test_long_text_is_shortened_and_marked() -> None:
    url = "http://example.com/long"
    transport = FakeTransport({url: html_response(url, fixture("long_page.html"))})

    article = read_page(
        url,
        settings=settings(max_source_chars=80, min_source_chars=20),
        transport=transport,
        resolve=public_resolve,
    )

    assert article.shortened is True
    assert len(article.text) == 80
    assert article.text.startswith("Carbon dioxide")


def test_plain_text_uses_the_host_as_the_title() -> None:
    url = "http://example.com/notes.txt"
    body = ("Plants make food from sunlight, water, and carbon dioxide. " * 12).encode()
    transport = FakeTransport(
        {
            url: FakeResponse(
                headers={"Content-Type": "text/plain; charset=utf-8"},
                body=body,
                url=url,
            )
        }
    )

    article = read_page(
        url,
        settings=settings(),
        transport=transport,
        resolve=public_resolve,
    )

    assert article.title == "example.com"
    assert article.headings == []
    assert "Plants make food from sunlight" in article.text


def test_request_sends_a_studymaster_user_agent_and_no_secrets() -> None:
    url = "http://example.com/plants"
    transport = FakeTransport({url: html_response(url, fixture("simple_article.html"))})

    read_page(url, settings=settings(), transport=transport, resolve=public_resolve)

    sent = transport.headers[0]
    assert "StudyMaster" in sent["User-Agent"]
    assert "Cookie" not in sent
    assert "Authorization" not in sent
    assert transport.timeouts == [10]


def test_unsupported_content_type_is_rejected() -> None:
    url = "http://example.com/file.pdf"
    transport = FakeTransport(
        {
            url: FakeResponse(
                headers={"Content-Type": "application/pdf"},
                body=b"%PDF",
                url=url,
            )
        }
    )

    with pytest.raises(UnsupportedContentError):
        read_page(url, settings=settings(), transport=transport, resolve=public_resolve)


def test_download_timeout_is_a_fetch_error() -> None:
    url = "http://example.com/slow"

    class TimeoutTransport:
        def get(self, url: str, *, timeout: float, headers: dict[str, str]):
            raise requests.Timeout("timed out")

    with pytest.raises(FetchError, match="could not be downloaded"):
        read_page(
            url,
            settings=settings(),
            transport=TimeoutTransport(),
            resolve=public_resolve,
        )


def test_sixth_redirect_is_rejected() -> None:
    hosts = [f"hop{index}.example.com" for index in range(7)]
    urls = [f"http://{host}/page" for host in hosts]
    routes = {
        urls[index]: FakeResponse(
            status_code=302,
            headers={"Location": urls[index + 1]},
            url=urls[index],
        )
        for index in range(6)
    }
    transport = FakeTransport(routes)

    with pytest.raises(FetchError, match="redirected too many times"):
        read_page(
            urls[0],
            settings=settings(),
            transport=transport,
            resolve=public_resolve,
        )

    assert transport.calls == urls[:6]


def test_logs_record_the_host_and_not_the_query(caplog: pytest.LogCaptureFixture) -> None:
    url = "http://example.com/plants?token=super-secret-token"
    transport = FakeTransport({url: html_response(url, fixture("simple_article.html"))})

    with caplog.at_level(logging.INFO):
        read_page(url, settings=settings(), transport=transport, resolve=public_resolve)

    assert "example.com" in caplog.text
    assert "super-secret-token" not in caplog.text
    assert "Page read failed" not in caplog.text
