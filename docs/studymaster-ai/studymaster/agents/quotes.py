"""Check that a quote was copied from the extracted page text."""

import re
from dataclasses import dataclass

COVER = "The source does not cover this."
_SKIP = frozenset(
    {
        "that",
        "this",
        "with",
        "from",
        "they",
        "their",
        "have",
        "what",
        "when",
        "your",
        "into",
        "does",
    }
)
_NEGATIONS = frozenset(
    {
        "not",
        "no",
        "nor",
        "never",
        "none",
        "nothing",
        "neither",
        "without",
        "cannot",
        "don't",
        "doesn't",
        "didn't",
        "isn't",
        "aren't",
        "wasn't",
        "weren't",
        "won't",
        "can't",
        "couldn't",
        "wouldn't",
        "shouldn't",
        "hasn't",
        "haven't",
        "hadn't",
    }
)
_WORD = re.compile(r"[a-z0-9']+")


@dataclass(frozen=True)
class CheckedQuote:
    """One quote and whether it appears in the source."""

    label: str
    quote: str
    grounded: bool


def quote_is_grounded(quote: str, source_text: str) -> bool:
    """Return True when the quote appears in the source.

    Extra spaces are ignored. A blank quote is not grounded.
    """
    needle = _normalize(quote)
    if not needle:
        return False
    return needle in _normalize(source_text)


def check_quote(label: str, quote: str, source_text: str) -> CheckedQuote:
    """Check one quote and keep its label."""
    return CheckedQuote(
        label=label,
        quote=quote.strip(),
        grounded=quote_is_grounded(quote, source_text),
    )


def grounding_line(checked: CheckedQuote) -> str:
    """Return the quote line, or a not-grounded warning."""
    if checked.grounded:
        return f"Quote: {checked.quote}"
    return "Not grounded."


def sentence_is_supported(text: str, quote: str, source_text: str) -> bool:
    """Return True when the sentence may be shown."""
    if not quote_is_grounded(quote, source_text):
        return False
    source_words = set(_tokens(source_text))
    if any(word not in source_words for word in _main_words(text)):
        return False
    if _has_negation(text) != _has_negation(quote):
        return False
    return _has_only(text) == _has_only(quote)


def shown_sentence(text: str, quote: str, source_text: str) -> str:
    """Return the sentence, or the line that the source does not cover it."""
    if sentence_is_supported(text, quote, source_text):
        return text.strip()
    return COVER


def quote_line(sentences: list[str], quote: str, source_text: str) -> str:
    """Return the quote line when any sentence in the group is kept."""
    if quote.strip() and any(
        sentence_is_supported(sentence, quote, source_text) for sentence in sentences
    ):
        return f"Quote: {quote.strip()}"
    return ""


def _normalize(text: str) -> str:
    return " ".join(text.split()).casefold()


def _tokens(text: str) -> list[str]:
    return _WORD.findall(text.replace("\u2019", "'").casefold())


def _main_words(text: str) -> list[str]:
    return [
        word
        for word in _tokens(text)
        if len(word) >= 4 and word not in _SKIP and word not in _NEGATIONS and word != "only"
    ]


def _has_negation(text: str) -> bool:
    return any(word in _NEGATIONS for word in _tokens(text))


def _has_only(text: str) -> bool:
    return "only" in _tokens(text)
