"""heritage-vocab — Offline vocabulary service for Getty AAT/ULAN/TGN terms.

Provides a simple search() interface over Cache & Carry's SQLite vocabulary
database, enabling sub-millisecond lookup of controlled terms for material
normalisation, period validation, and artefact classification.

Usage:
    from heritage_vocab import VocabularyService

    svc = VocabularyService()
    results = svc.search("flint", vocabulary="aat", limit=5)
    # → [{"id": "http://vocab.getty.edu/aat/300011754",
    #      "label": "Flint/Chert", "source": "aat", ...}]
"""

from heritage_vocab.service import VocabularyService, VocabTerm

__all__ = ["VocabularyService", "VocabTerm"]
