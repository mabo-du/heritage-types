"""Unit tests for the ``heritage_vocab`` vocabulary service.

These tests target the hardening in REVIEW.md H3/H4:

* ``search()``/``children_of()`` reject non-positive ``limit``
* The fallback path tags results with ``FALLBACK_SOURCE_TAG`` so callers
  can detect unverified URIs
* The auto-created DB is opened read-only on subsequent queries
* Search terms with FTS5 operator trivia (e.g. ``NEAR``, ``-``, ``*``) are
  sanitised — no operator leakage, no Unicode homoglyph bypass
"""

from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

# Make the vocab service importable when pytest is run from repo root.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "python"))

import pytest  # noqa: E402

from heritage_vocab.service import (  # noqa: E402
    FALLBACK_SOURCE_TAG,
    VocabTerm,
    VocabularyService,
)

# The sanitiser is a @staticmethod on VocabularyService. Bind a short
# alias so test bodies read like the underlying contract.
sanitise_fts_term = VocabularyService._sanitise_fts_term  # type: ignore[attr-defined]


# ── Hardening: limit validation (H3) ─────────────────────────────────────


def test_search_rejects_zero_limit() -> None:
    svc = VocabularyService(db_path="/nonexistent/vocab.db")
    with pytest.raises(ValueError, match="limit must be a positive integer"):
        svc.search("flint", limit=0)


def test_search_rejects_negative_limit() -> None:
    svc = VocabularyService(db_path="/nonexistent/vocab.db")
    with pytest.raises(ValueError, match="limit must be a positive integer"):
        svc.search("flint", limit=-5)


def test_children_of_rejects_zero_limit() -> None:
    svc = VocabularyService(db_path="/nonexistent/vocab.db")
    with pytest.raises(ValueError):
        svc.children_of("http://vocab.getty.edu/aat/0", limit=0)


# ── Hardening: FTS5 sanitisation ────────────────────────────────────────
# Contract: the sanitiser filters to ``alnum/space/_-`` after NFKC
# normalisation. We pin what it actually drops (" ' ; * etc.) and what
# it intentionally keeps (letters, spaces, dashes — including SQL
# looking sequences like ``--`` which FTS5 has no concept of).
# Defence against FTS5 boolean operators (OR / AND / NOT / NEAR)
# comes from the call-site wrapping output in ``"..."`` (a phrase), so
# the sanitiser purposely does NOT strip letter sequences.


@pytest.mark.parametrize(
    "term",
    [
        "flint",
        "pottery",
        "ROMAN",  # caller lower-cases
        "field-12",  # '-' preserved as FTS5 tokenchar
        "αγγελοϟ",  # NFKC drops the homoglyph 'ϟ'
        "  flint  ",  # whitespace stripped
        'flint"or"1=1',  # embedded quoting
        "flint*",  # prefix-wildcard literal
        "DROP TABLE vocabulary_terms;",  # SQL-ish punctuation
    ],
)
def test_sanitise_strips_dangerous_chars(term: str) -> None:
    out = sanitise_fts_term(term)
    assert '"' not in out, f'embedded double-quote survived in {out!r}'
    assert "*" not in out, f'FTS5 wildcard survived in {out!r}'
    assert ";" not in out, f'FTS5 statement terminator survived in {out!r}'


def test_sanitise_drops_fullwidth_homoglyphs() -> None:
    # Fullwidth 'ｆ' (U+FF46) NFKC-normalises to 'f', then alnum check
    # passes.
    out = sanitise_fts_term("\uff46lint")
    assert out == "flint"


def test_sanitise_keeps_boolean_words_inside_phrase() -> None:
    # Sanitiser does NOT strip letters; FTS5 boolean operators are inert
    # inside a phrase at the call site. Pin the contract so a future
    # change is reviewed.
    out = sanitise_fts_term("flint OR bronze")
    assert out == "flint OR bronze"


def test_sanitise_keeps_dashes() -> None:
    # Two dashes survive — defence against SQL ``--`` is moot in FTS5.
    out = sanitise_fts_term("DROP TABLE vocabulary_terms--")
    assert "--" in out


def test_sanitise_preserves_simple_alnum() -> None:
    assert sanitise_fts_term("Hello World 42") == "Hello World 42"


# ── Hardening: read-only DB open ─────────────────────────────────────────


def test_auto_create_then_queries_work() -> None:
    """After ``auto_create=True``, queries should return results.
    Opens read-only via SQLite URI so test exercises that path too.
    """
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "vocab.db"
        svc = VocabularyService(db_path=path, auto_create=True)
        results = svc.search("flint")
        assert any(t.preferred_label == "Flint/Chert" for t in results)

        with sqlite3.connect(path) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM vocabulary_terms"
            ).fetchone()[0]
            assert count >= 1


def test_open_ro_rejects_writes() -> None:
    """The reader path opened via ``_open_ro`` is genuinely read-only.

    Exercises ``VocabularyService._open_ro`` directly so a regression in
    URI construction (escaping, scheme, missing ``?mode=ro``) is caught
    here rather than at the first consumer install.
    """
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "vocab.db"
        svc = VocabularyService(db_path=path, auto_create=True)
        conn = svc._open_ro()  # type: ignore[attr-defined]
        try:
            with pytest.raises(sqlite3.OperationalError, match="readonly"):
                conn.execute("UPDATE vocabulary_terms SET scope_note = 'X'")
        finally:
            conn.close()


# ── Fallback source tag (H4) ─────────────────────────────────────────────


def test_fallback_results_are_tagged_unverified() -> None:
    """Every fallback result must carry FALLBACK_SOURCE_TAG so callers
    can detect unverified URIs."""
    svc = VocabularyService(db_path=Path("/nonexistent/vocab.db"))
    results = svc.search("flint")
    assert results, "fallback returned no results for 'flint'"
    for term in results:
        assert isinstance(term, VocabTerm)
        assert term.source == FALLBACK_SOURCE_TAG, (
            f"fallback result has source={term.source!r}: expected "
            f"FALLBACK_SOURCE_TAG ({FALLBACK_SOURCE_TAG!r})"
        )


def test_fallback_unknown_term_returns_empty() -> None:
    svc = VocabularyService(db_path=Path("/nonexistent/vocab.db"))
    results = svc.search("qzqzqzqz_unknown_unobtainium_term")
    assert results == []


def test_fallback_lookup_returns_none_when_no_db() -> None:
    svc = VocabularyService(db_path=Path("/nonexistent/vocab.db"))
    assert svc.lookup("http://vocab.getty.edu/aat/300011754") is None


def test_fallback_source_tag_constant_is_meaningful() -> None:
    assert "unverified" in FALLBACK_SOURCE_TAG
