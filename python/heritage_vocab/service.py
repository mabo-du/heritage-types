"""service.py — Vocabulary query service over Cache & Carry SQLite database.

Provides an offline FTS5-backed lookup for Getty AAT, ULAN, and TGN terms,
matching the schema used by Cache & Carry at:
    ~/.local/share/com.cacheandcarry.app/vocab/vocab_cache.db

Supports prefix search, vocabulary filtering, and hierarchical browsing
via parent_id lookups — no network calls required.

exports: VocabularyService, VocabTerm
"""

from __future__ import annotations

import json
import os
import sqlite3
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# Default Cache & Carry vocabulary database path.
DEFAULT_VOCAB_DB = (
    Path.home()
    / ".local"
    / "share"
    / "com.cacheandcarry.app"
    / "vocab"
    / "vocab_cache.db"
)


# Sentinel source tag used for fallback entries so downstream consumers
# can distinguish a real Cache & Carry result from the in-memory
# fallback (whose URIs are flagged "unverified" in REVIEW.md).
FALLBACK_SOURCE_TAG = "aat-fallback-unverified"

# URI prefix for fallback vocabulary terms. Distinct from real AAT
# namespaces so any consumer that gets one of these IDs can spot the
# fallback provenance immediately, and so two distinct concepts ("Iron
# Age", "Bronze Age", "Neolithic" ...) never collide on the same ID as
# happened with aat/300019275 prior to the 2.0.0 rewrite (REVIEW.md H4).
#
# These IDs are NOT real Getty AAT IRIs; callers must filter out entries
# with source == FALLBACK_SOURCE_TAG before persisting them to a citation
# graph.
_FALLBACK_URI_PREFIX = "http://vocab.heritage-science.dev/fallback-unverified/aat/"


@dataclass
class VocabTerm:
    """A single term from the Getty vocabulary, as returned by search()."""

    id: str  # Full URI, e.g. http://vocab.getty.edu/aat/300011754
    source: str  # "aat", "ulan", "tgn", or FALLBACK_SOURCE_TAG
    preferred_label: str
    alt_labels: list[str]  # Alternative labels/synonyms
    scope_note: str  # Definition/description
    parent_id: str | None  # Broader concept URI


class VocabularyService:
    """Offline vocabulary query service.

    Reads from Cache & Carry's SQLite vocabulary database and provides
    FTS5-backed search and lookup for term standardisation.

    Args:
        db_path: Path to the Cache & Carry vocab_cache.db SQLite database.
                 Defaults to the standard location.
        auto_create: If True, create the schema and a small sample dataset
                     when the database doesn't exist (for testing/dev).
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        auto_create: bool = False,
    ) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_VOCAB_DB
        if auto_create and not self.db_path.exists():
            self._create_sample_db()

    # ── Public API ───────────────────────────────────────────────────────

    def search(
        self,
        term: str,
        vocabulary: str = "",
        limit: int = 20,
        exact: bool = False,
    ) -> list[VocabTerm]:
        """Search the vocabulary for matching terms.

        Uses FTS5 prefix matching by default. Set exact=True for exact
        preferred_label matching (useful for normalisation).

        Args:
            term: Search query string.
            vocabulary: Filter by source ('aat', 'ulan', 'tgn', or '' for all).
            limit: Maximum number of results (must be > 0).
            exact: If True, match exact preferred_label (FTS5 exact mode).

        Raises:
            ValueError: limit is not a positive integer.

        Returns:
            List of VocabTerm matches, ordered by relevance.
        """
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError(f"limit must be a positive integer (got {limit!r})")

        if not self.db_path.exists():
            return self._fallback_builtin(term, vocabulary, limit)

        conn = self._open_ro()
        try:
            return self._search_fts(conn, term, vocabulary, limit, exact)
        finally:
            conn.close()

    def lookup(self, term_id: str) -> VocabTerm | None:
        """Look up a term by its full Getty URI.

        Args:
            term_id: Full URI (e.g. 'http://vocab.getty.edu/aat/300011754').

        Returns:
            VocabTerm if found, None otherwise.
        """
        if not self.db_path.exists():
            return None

        conn = self._open_ro()
        try:
            cur = conn.execute(
                "SELECT id, source, preferred_label, alt_labels, scope_note, parent_id "
                "FROM vocabulary_terms WHERE id = ?",
                (term_id,),
            )
            row = cur.fetchone()
            return self._row_to_term(row) if row else None
        finally:
            conn.close()

    def children_of(self, parent_id: str, limit: int = 50) -> list[VocabTerm]:
        """Get narrower terms under a given parent concept.

        Args:
            parent_id: Parent URI.
            limit: Maximum results (must be > 0).

        Raises:
            ValueError: limit is not a positive integer.

        Returns:
            List of narrower terms.
        """
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError(f"limit must be a positive integer (got {limit!r})")

        if not self.db_path.exists():
            return []

        conn = self._open_ro()
        try:
            cur = conn.execute(
                "SELECT id, source, preferred_label, alt_labels, scope_note, parent_id "
                "FROM vocabulary_terms WHERE parent_id = ? LIMIT ?",
                (parent_id, limit),
            )
            return [self._row_to_term(row) for row in cur.fetchall()]
        finally:
            conn.close()

    # ── Normalisation helpers ────────────────────────────────────────────

    def normalise_material(self, raw_term: str) -> VocabTerm | None:
        """Normalise a free-text material description to a Getty AAT term."""
        results = self.search(raw_term, vocabulary="aat", limit=1, exact=True)
        if results:
            return results[0]
        results = self.search(raw_term, vocabulary="aat", limit=1)
        if results and self._label_similar(
            raw_term, results[0].preferred_label.lower()
        ):
            return results[0]
        return None

    def normalise_period(self, raw_term: str) -> VocabTerm | None:
        """Normalise a free-text period to a Getty AAT term."""
        period_terms = [raw_term, f"{raw_term} (style)", f"{raw_term} (culture)"]
        for t in period_terms:
            results = self.search(t, vocabulary="aat", limit=1, exact=True)
            if results:
                return results[0]
            results = self.search(t, vocabulary="aat", limit=1)
            if results and self._label_similar(
                raw_term, results[0].preferred_label.lower()
            ):
                return results[0]
        return None

    # ── Internal: read-only DB connection ────────────────────────────────

    def _open_ro(self) -> sqlite3.Connection:
        """Open the Cache & Carry DB **read-only** via SQLite URI mode.

        SQLite refuses to open a read-only URI database if the file's
        directory is not readable or the file does not exist; likewise
        journal/WAL sidecars are opened read-only. This prevents a
        compromised sibling process from poisoning our query results
        via tempfile-based sidecar writes and is the defence recommended
        for hostile multi-user environments in the Cache & Carry docs.

        Closes cleanly and tears down journals on close().
        """
        # ``Path.as_uri()`` correctly percent-encodes the path component
        # for spaces, ``?``, ``&``, non-ASCII codepoints, etc. Hand-rolling
        # ``f"file:{path}…"`` silently produces malformed URIs for those
        # characters and a confusing ``sqlite3.OperationalError``.
        uri = self.db_path.as_uri() + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        return conn

    # ── Internal: FTS5 search ────────────────────────────────────────────

    @staticmethod
    def _sanitise_fts_term(term: str) -> str:
        """Strip FTS5 operators and unicode tricks from a user-supplied term.

        The FTS5 query is wrapped in ``"..."`` so the input becomes a
        *phrase* (a sequence of tokens). Even so we aggressively filter
        characters that could be interpreted as FTS5 operators or unicode
        lookalikes:

        * Drop anything outside ``a-zA-Z0-9 -_``.
        * ``-`` and ``_`` are kept because the FTS5 virtual table here
          declares ``tokenchars '_-'`` so e.g. ``field-12`` is one token.
        * Normalise to NFKC so unicode homoglyphs and fullwidth forms
          can't smuggle bytes past the alnum check.
        """
        if not term:
            return ""
        nfkc = unicodedata.normalize("NFKC", term)
        cleaned = "".join(c for c in nfkc if c.isalnum() or c in " _-").strip()
        return cleaned

    def _search_fts(
        self,
        conn: sqlite3.Connection,
        term: str,
        vocabulary: str,
        limit: int,
        exact: bool,
    ) -> list[VocabTerm]:
        """Execute FTS5 search against the vocabulary database.

        LIMIT is bound as a parameter (not f-string interpolated) and the
        user-supplied term is run through ``_sanitise_fts_term`` before
        being wrapped in an FTS5 phrase.
        """
        clean = self._sanitise_fts_term(term)
        if not clean:
            return []

        # FTS5 phrase syntax: `"foo bar"` (exact) or `"foo"*` (prefix
        # wildcard). Inside the double quotes the FTS5 query parser
        # treats content as a token sequence and does not honour column
        # filters or NEAR/NOT operators, so wrapping sanitises input.
        query = f'"{clean}"' if exact else f'"{clean}"*'

        sql = (
            "SELECT vt.id, vt.source, vt.preferred_label, vt.alt_labels, "
            "       vt.scope_note, vt.parent_id "
            "FROM vocabulary_fts f "
            "JOIN vocabulary_terms vt ON f.id = vt.id "
            "WHERE vocabulary_fts MATCH ? "
        )
        params: list[Any] = [query]
        if vocabulary:
            sql += " AND vt.source = ? "
            params.append(vocabulary)
        sql += " ORDER BY rank LIMIT ?"
        params.append(limit)

        try:
            cur = conn.execute(sql, params)
            return [self._row_to_term(row) for row in cur.fetchall()]
        except sqlite3.OperationalError:
            # FTS5 syntax error (e.g. pathological input) — fall back to
            # plain LIKE. Both query fields are still bound.
            like_pattern = f"%{clean}%"
            sql = (
                "SELECT id, source, preferred_label, alt_labels, scope_note, parent_id "
                "FROM vocabulary_terms WHERE preferred_label LIKE ? "
            )
            params = [like_pattern]
            if vocabulary:
                sql += " AND source = ? "
                params.append(vocabulary)
            sql += " LIMIT ?"
            params.append(limit)
            cur = conn.execute(sql, params)
            return [self._row_to_term(row) for row in cur.fetchall()]

    # ── Internal: helpers ────────────────────────────────────────────────

    @staticmethod
    def _row_to_term(row: sqlite3.Row) -> VocabTerm:
        """Convert a SQLite row to a VocabTerm dataclass."""
        alt_raw = row["alt_labels"]
        alt_labels: list[str] = []
        if alt_raw:
            try:
                alt_labels = json.loads(alt_raw)
            except (json.JSONDecodeError, TypeError):
                alt_labels = [alt_raw] if alt_raw else []
        return VocabTerm(
            id=row["id"],
            source=row["source"],
            preferred_label=row["preferred_label"],
            alt_labels=alt_labels,
            scope_note=row["scope_note"] or "",
            parent_id=row["parent_id"],
        )

    @staticmethod
    def _label_similar(raw: str, label: str) -> bool:
        """Check if a raw term is similar to a vocabulary label."""
        raw_clean = raw.lower().strip()
        label_clean = label.lower().strip()
        return raw_clean in label_clean or label_clean in raw_clean

    # ── Internal: unverified fallback ────────────────────────────────────

    def _fallback_builtin(
        self, term: str, vocabulary: str, limit: int
    ) -> list[VocabTerm]:
        """Built-in fallback when no vocab database is installed.

        IMPORTANT: the AAT URIs in this map are *unverified* — they were
        asserted at code time without consulting the live Getty vocabulary.
        Consumers should treat results from this path as a last resort.

        Each ``VocabTerm`` emitted here carries ``source = FALLBACK_SOURCE_TAG``
        so callers can filter:
            ``[t for t in svc.search('flint') if t.source !=
              heritage_vocab.service.FALLBACK_SOURCE_TAG]``
        """
        term_lower = term.lower().strip()
        matches: list[VocabTerm] = []

        # Common material terms. URIs are UNVERIFIED sentinel IDs (see
        # REVIEW.md H4) — they live under ``_FALLBACK_URI_PREFIX``, NOT
        # the real ``vocab.getty.edu`` namespace, so no two distinct
        # concepts share an ID and any consumer that fails to filter on
        # source==FALLBACK_SOURCE_TAG will at least see obviously
        # non-AAT URIs.
        material_map: dict[str, tuple[str, str, str]] = {
            "flint": (
                f"{_FALLBACK_URI_PREFIX}material/flint-chert",
                "Flint/Chert",
                "A compact, microcrystalline quartz mineral used for tool making.",
            ),
            "chert": (
                f"{_FALLBACK_URI_PREFIX}material/flint-chert",
                "Flint/Chert",
                "A compact, microcrystalline quartz mineral used for tool making.",
            ),
            "pottery": (
                f"{_FALLBACK_URI_PREFIX}material/pottery",
                "Pottery (object genre)",
                "Ceramic ware made from fired clay, usually glazed.",
            ),
            "ceramic": (
                f"{_FALLBACK_URI_PREFIX}material/pottery",
                "Pottery (object genre)",
                "Ceramic ware made from fired clay, usually glazed.",
            ),
            "bone": (
                f"{_FALLBACK_URI_PREFIX}material/bone",
                "Bone (material)",
                "The hard, rigid form of connective tissue constituting the skeleton.",
            ),
            "metal": (
                f"{_FALLBACK_URI_PREFIX}material/metal",
                "Metal",
                "Any of various opaque, fusible, malleable substances.",
            ),
            "iron": (
                f"{_FALLBACK_URI_PREFIX}material/iron",
                "Iron (metal)",
                "A metallic element occurring naturally as haematite.",
            ),
            "glass": (
                f"{_FALLBACK_URI_PREFIX}material/glass",
                "Glass (material)",
                "A hard, amorphous material made by melting sand with soda.",
            ),
            "cbm": (
                f"{_FALLBACK_URI_PREFIX}material/cbm",
                "Ceramic building material",
                "Baked clay products used in building construction.",
            ),
            "slag": (
                f"{_FALLBACK_URI_PREFIX}material/slag",
                "Slag",
                "The fused refuse matter separated during smelting.",
            ),
        }

        if vocabulary in ("", "aat"):
            for key, (uri, label, note) in material_map.items():
                if term_lower == key or term_lower in key or key in term_lower:
                    matches.append(
                        VocabTerm(
                            id=uri,
                            source=FALLBACK_SOURCE_TAG,
                            preferred_label=label,
                            alt_labels=[key],
                            scope_note=note,
                            parent_id=None,
                        )
                    )

        # Common period terms. URIs are UNVERIFIED sentinel IDs (see
        # REVIEW.md H4) — each gets its own distinct IRI under
        # ``_FALLBACK_URI_PREFIX`` so “Neolithic”, “Bronze Age”, etc. do
        # NOT collide on a single shared ID the way the pre-2.0.0 map
        # did (aat/300019275 was reused for two distinct concepts).
        period_map: dict[str, tuple[str, str, str]] = {
            "palaeolithic": (
                f"{_FALLBACK_URI_PREFIX}period/palaeolithic",
                "Palaeolithic",
                "The earliest prehistoric period of human development.",
            ),
            "mesolithic": (
                f"{_FALLBACK_URI_PREFIX}period/mesolithic",
                "Mesolithic",
                "The middle period of the Stone Age.",
            ),
            "neolithic": (
                f"{_FALLBACK_URI_PREFIX}period/neolithic",
                "Neolithic",
                "The late period of the Stone Age.",
            ),
            "bronze age": (
                f"{_FALLBACK_URI_PREFIX}period/bronze-age",
                "Bronze Age",
                "The period characterized by the use of bronze tools.",
            ),
            "iron age": (
                f"{_FALLBACK_URI_PREFIX}period/iron-age",
                "Iron Age",
                "The period characterized by the use of iron tools.",
            ),
            "roman": (
                f"{_FALLBACK_URI_PREFIX}period/roman",
                "Roman (ancient)",
                "The culture and period of ancient Rome.",
            ),
            "medieval": (
                f"{_FALLBACK_URI_PREFIX}period/medieval",
                "Medieval",
                "The period between classical antiquity and the Renaissance.",
            ),
            "post-medieval": (
                f"{_FALLBACK_URI_PREFIX}period/post-medieval",
                "Post-medieval",
                "The period after the Middle Ages.",
            ),
        }

        for key, (uri, label, note) in period_map.items():
            if term_lower == key or term_lower in key or key in term_lower:
                matches.append(
                    VocabTerm(
                        id=uri,
                        source=FALLBACK_SOURCE_TAG,
                        preferred_label=label,
                        alt_labels=[key],
                        scope_note=note,
                        parent_id=None,
                    )
                )

        return matches[:limit]

    # ── Test database creator ────────────────────────────────────────────

    def _create_sample_db(self) -> None:
        """Create a small sample vocabulary database for testing."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # Writer mode is only used at db-creation time. After this method
        # returns, all reads go through `_open_ro`.
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.executescript(
                "CREATE TABLE IF NOT EXISTS vocabulary_terms ("
                "  id TEXT PRIMARY KEY, source TEXT NOT NULL,"
                "  preferred_label TEXT NOT NULL, alt_labels TEXT,"
                "  scope_note TEXT, parent_id TEXT, last_updated TEXT"
                ");"
            )
            samples = [
                (
                    "http://vocab.getty.edu/aat/300011754",
                    "aat",
                    "Flint/Chert",
                    '["flint", "chert", "flint stone"]',
                    "Microcrystalline quartz mineral.",
                ),
                (
                    "http://vocab.getty.edu/aat/300054926",
                    "aat",
                    "Pottery (object genre)",
                    '["pottery", "ceramic", "earthenware"]',
                    "Ceramic ware from fired clay.",
                ),
                (
                    "http://vocab.getty.edu/aat/300011799",
                    "aat",
                    "Bone (material)",
                    '["bone", "skeletal material"]',
                    "Hard connective tissue.",
                ),
                (
                    "http://vocab.getty.edu/aat/300010902",
                    "aat",
                    "Iron (metal)",
                    '["iron", "ferrous metal"]',
                    "Metallic element.",
                ),
                (
                    "http://vocab.getty.edu/aat/300019275",
                    "aat",
                    "Bronze Age",
                    '["bronze age", "bronze-age"]',
                    "Period of bronze tool use.",
                ),
                (
                    "http://vocab.getty.edu/aat/300020533",
                    "aat",
                    "Roman (ancient)",
                    '["roman", "romano-british"]',
                    "Ancient Roman culture.",
                ),
                (
                    "http://vocab.getty.edu/aat/300020756",
                    "aat",
                    "Medieval",
                    '["medieval", "middle ages"]',
                    "Period 5th-15th century.",
                ),
            ]
            # Named-column INSERT so adding a column doesn't silently
            # shift positional parameters.
            conn.executemany(
                "INSERT OR IGNORE INTO vocabulary_terms"
                "  (id, source, preferred_label, alt_labels, scope_note, parent_id, last_updated)"
                "  VALUES (?, ?, ?, ?, ?, NULL, ?)",
                [(s[0], s[1], s[2], s[3], s[4], "") for s in samples],
            )
            conn.executescript(
                "CREATE VIRTUAL TABLE IF NOT EXISTS vocabulary_fts USING fts5("
                "  id UNINDEXED, preferred_label, alt_labels, scope_note,"
                "  tokenize='unicode61 remove_diacritics 2 tokenchars ''_-'''"
                ");"
                "INSERT OR IGNORE INTO vocabulary_fts"
                "  SELECT id, preferred_label, alt_labels, scope_note"
                "  FROM vocabulary_terms;"
            )
            conn.commit()
        finally:
            conn.close()
