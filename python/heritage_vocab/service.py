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
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# Default Cache & Carry vocabulary database path
DEFAULT_VOCAB_DB = (
    Path.home()
    / ".local"
    / "share"
    / "com.cacheandcarry.app"
    / "vocab"
    / "vocab_cache.db"
)


@dataclass
class VocabTerm:
    """A single term from the Getty vocabulary, as returned by search()."""

    id: str  # Full URI, e.g. http://vocab.getty.edu/aat/300011754
    source: str  # "aat", "ulan", "tgn"
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
            limit: Maximum number of results.
            exact: If True, match exact preferred_label (FTS5 exact mode).

        Returns:
            List of VocabTerm matches, ordered by relevance.
        """
        if not self.db_path.exists():
            return self._fallback_builtin(term, vocabulary, limit)

        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
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

        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
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
            limit: Maximum results.

        Returns:
            List of narrower terms.
        """
        if not self.db_path.exists():
            return []

        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
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
        """Normalise a free-text material description to a Getty AAT term.

        Tries exact match first, then prefix search, returns the highest-
        confidence match. Useful for HOARD Phase 1 post-processing.

        Args:
            raw_term: Free-text material string (e.g. 'flint', 'pottery').

        Returns:
            The best matching VocabTerm, or None.
        """
        results = self.search(raw_term, vocabulary="aat", limit=1, exact=True)
        if results:
            return results[0]
        results = self.search(raw_term, vocabulary="aat", limit=1)
        if results and self._label_similar(raw_term, results[0].preferred_label.lower()):
            return results[0]
        return None

    def normalise_period(self, raw_term: str) -> VocabTerm | None:
        """Normalise a free-text period to a Getty AAT term.

        Args:
            raw_term: Free-text period string (e.g. 'bronze age', 'medieval').

        Returns:
            The best matching VocabTerm, or None.
        """
        # Try with period-specific search terms
        period_terms = [raw_term, f"{raw_term} (style)", f"{raw_term} (culture)"]
        for t in period_terms:
            results = self.search(t, vocabulary="aat", limit=1, exact=True)
            if results:
                return results[0]
            results = self.search(t, vocabulary="aat", limit=1)
            if results:
                return results[0]
        return None

    # ── Internal: FTS5 search ────────────────────────────────────────────

    def _search_fts(
        self,
        conn: sqlite3.Connection,
        term: str,
        vocabulary: str,
        limit: int,
        exact: bool,
    ) -> list[VocabTerm]:
        """Execute FTS5 search against the vocabulary database."""
        # Sanitise the query for FTS5 (remove special chars, wrap in quotes)
        clean = "".join(c for c in term if c.isalnum() or c in " _-").strip()
        if not clean:
            return []

        if exact:
            query = f'"{clean}"'
        else:
            query = f'"{clean}"*'  # Prefix match (FTS5 suffix wildcard)

        sql = (
            "SELECT vt.id, vt.source, vt.preferred_label, vt.alt_labels, "
            "       vt.scope_note, vt.parent_id "
            "FROM vocabulary_fts f "
            "JOIN vocabulary_terms vt ON f.id = vt.id "
            "WHERE vocabulary_fts MATCH ?"
        )
        params: list[Any] = [query]

        if vocabulary:
            sql += " AND vt.source = ?"
            params.append(vocabulary)

        sql += f" ORDER BY rank LIMIT {int(limit)}"

        try:
            cur = conn.execute(sql, params)
            return [self._row_to_term(row) for row in cur.fetchall()]
        except sqlite3.OperationalError:
            # FTS5 syntax error (e.g. single-char words) — fallback to LIKE
            like_pattern = f"%{clean}%"
            sql = (
                "SELECT id, source, preferred_label, alt_labels, scope_note, parent_id "
                "FROM vocabulary_terms WHERE preferred_label LIKE ?"
            )
            params = [like_pattern]
            if vocabulary:
                sql += " AND source = ?"
                params.append(vocabulary)
            sql += f" LIMIT {int(limit)}"
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

    def _fallback_builtin(
        self, term: str, vocabulary: str, limit: int
    ) -> list[VocabTerm]:
        """Built-in fallback when no vocab database is installed.

        Covers the most common archaeological terms so HOARD can still
        normalise basic materials and periods without Cache & Carry.
        """
        term_lower = term.lower().strip()
        matches: list[VocabTerm] = []

        # Common material terms
        material_map: dict[str, tuple[str, str, str]] = {
            "flint": ("http://vocab.getty.edu/aat/300011754", "Flint/Chert",
                      "A compact, microcrystalline quartz mineral used for tool making."),
            "chert": ("http://vocab.getty.edu/aat/300011754", "Flint/Chert",
                      "A compact, microcrystalline quartz mineral used for tool making."),
            "pottery": ("http://vocab.getty.edu/aat/300054926", "Pottery (object genre)",
                        "Ceramic ware made from fired clay, usually glazed."),
            "ceramic": ("http://vocab.getty.edu/aat/300054926", "Pottery (object genre)",
                        "Ceramic ware made from fired clay, usually glazed."),
            "bone": ("http://vocab.getty.edu/aat/300011799", "Bone (material)",
                     "The hard, rigid form of connective tissue constituting the skeleton."),
            "metal": ("http://vocab.getty.edu/aat/300010900", "Metal",
                      "Any of various opaque, fusible, malleable substances."),
            "iron": ("http://vocab.getty.edu/aat/300010902", "Iron (metal)",
                     "A metallic element occurring naturally as haematite."),
            "glass": ("http://vocab.getty.edu/aat/300010797", "Glass (material)",
                      "A hard, amorphous material made by melting sand with soda."),
            "cbm": ("http://vocab.getty.edu/aat/300015343", "Ceramic building material",
                    "Baked clay products used in building construction."),
            "slag": ("http://vocab.getty.edu/aat/300011798", "Slag",
                     "The fused refuse matter separated during smelting."),
        }

        if vocabulary in ("", "aat"):
            for key, (uri, label, note) in material_map.items():
                if term_lower == key or term_lower in key or key in term_lower:
                    matches.append(VocabTerm(
                        id=uri, source="aat", preferred_label=label,
                        alt_labels=[key], scope_note=note, parent_id=None,
                    ))

        # Common period terms
        period_map: dict[str, tuple[str, str, str]] = {
            "palaeolithic": ("http://vocab.getty.edu/aat/300019259", "Palaeolithic",
                             "The earliest prehistoric period of human development."),
            "mesolithic": ("http://vocab.getty.edu/aat/300019267", "Mesolithic",
                           "The middle period of the Stone Age."),
            "neolithic": ("http://vocab.getty.edu/aat/300019275", "Neolithic",
                          "The late period of the Stone Age."),
            "bronze age": ("http://vocab.getty.edu/aat/300019275", "Bronze Age",
                           "The period characterized by the use of bronze tools."),
            "iron age": ("http://vocab.getty.edu/aat/300019284", "Iron Age",
                         "The period characterized by the use of iron tools."),
            "roman": ("http://vocab.getty.edu/aat/300020533", "Roman (ancient)",
                      "The culture and period of ancient Rome."),
            "medieval": ("http://vocab.getty.edu/aat/300020756", "Medieval",
                         "The period between classical antiquity and the Renaissance."),
            "post-medieval": ("http://vocab.getty.edu/aat/300020752", "Post-medieval",
                              "The period after the Middle Ages."),
        }

        for key, (uri, label, note) in period_map.items():
            if term_lower == key or term_lower in key or key in term_lower:
                matches.append(VocabTerm(
                    id=uri, source="aat", preferred_label=label,
                    alt_labels=[key], scope_note=note, parent_id=None,
                ))

        return matches[:limit]

    # ── Test database creator ────────────────────────────────────────────

    def _create_sample_db(self) -> None:
        """Create a small sample vocabulary database for testing."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.executescript(
                "CREATE TABLE IF NOT EXISTS vocabulary_terms ("
                "  id TEXT PRIMARY KEY, source TEXT NOT NULL,"
                "  preferred_label TEXT NOT NULL, alt_labels TEXT,"
                "  scope_note TEXT, parent_id TEXT, last_updated TEXT"
                ");"
            )
            # Insert sample data (common archaeological terms)
            samples = [
                ("http://vocab.getty.edu/aat/300011754", "aat", "Flint/Chert",
                 '["flint", "chert", "flint stone"]', "Microcrystalline quartz mineral."),
                ("http://vocab.getty.edu/aat/300054926", "aat", "Pottery (object genre)",
                 '["pottery", "ceramic", "earthenware"]', "Ceramic ware from fired clay."),
                ("http://vocab.getty.edu/aat/300011799", "aat", "Bone (material)",
                 '["bone", "skeletal material"]', "Hard connective tissue."),
                ("http://vocab.getty.edu/aat/300010902", "aat", "Iron (metal)",
                 '["iron", "ferrous metal"]', "Metallic element."),
                ("http://vocab.getty.edu/aat/300019275", "aat", "Bronze Age",
                 '["bronze age", "bronze-age"]', "Period of bronze tool use."),
                ("http://vocab.getty.edu/aat/300020533", "aat", "Roman (ancient)",
                 '["roman", "romano-british"]', "Ancient Roman culture."),
                ("http://vocab.getty.edu/aat/300020756", "aat", "Medieval",
                 '["medieval", "middle ages"]', "Period 5th-15th century."),
            ]
            conn.executemany(
                "INSERT OR IGNORE INTO vocabulary_terms VALUES (?,?,?,?,?, NULL, ?)",
                [(s[0], s[1], s[2], s[3], s[4], "") for s in samples],
            )
            # Create FTS5 table
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
