"""Round-trip tests for the auto-generated ``heritage_models`` package.

These tests exercise the regenerated Pydantic v2 models against the
canonical JSON Schema. They are deliberately structural (no fixtures
or network) so they can run in under a second on every CI push.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

# Ensure the auto-generated ``heritage_models`` package is importable
# when pytest is invoked from the repo root.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "python"))

import pytest  # noqa: E402

# These imports fail loudly when C1/C2 regress.
from heritage_models import (  # noqa: E402
    AgentType,
    Chronology,
    DigitalAsset,
    Find,
    HeritageDataPackage,
    MaterialClass,
    ProvenanceActivity,
    ProvenanceAgent,
    ProvenanceRecord,
    RelationshipType,
    Sample,
    SampleType,
    SiteMetadata,
    StratigraphicRelationship,
    StratigraphicUnit,
    UnitType,
)
from heritage_models.models import HDP  # noqa: E402,F401 \u2014 proving C1 is fixed


REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schemas" / "heritage-data-package-v1.json"


def test_datetime_rejects_invalid_and_timezone_naive_values() -> None:
    """Generated date-time fields enforce syntax and timezone awareness."""
    from pydantic import ValidationError

    from heritage_models import Datetime

    with pytest.raises(ValidationError):
        Datetime.model_validate("not-a-date")
    with pytest.raises(ValidationError):
        Datetime.model_validate("2026-07-17T12:00:00")

    assert Datetime.model_validate("2026-07-17T12:00:00Z").root.tzinfo is not None


@pytest.fixture(scope="module")
def canonical_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text())


# ── Schema-shape regression tests (catch C1, M9, M8 fix regressions) ──────


def test_heritage_data_package_is_real_model_not_rootwrapper() -> None:
    """C1 regression guard: ``HeritageDataPackage`` must be a ``BaseModel``.

    Before the fix it was a ``RootModel[Any]`` (useless wrapper), with
    the real schema renamed to the cryptic ``HeritageDataPackage1``.
    """
    from pydantic import BaseModel

    assert issubclass(HeritageDataPackage, BaseModel), (
        f"HeritageDataPackage is {HeritageDataPackage!r}; expected BaseModel subclass"
    )
    # The old bugged module attribute must no longer exist.
    import heritage_models.models as m

    assert not hasattr(m, "HeritageDataPackage1"), (
        "HeritageDataPackage1 still exists — codegen name collision regression."
    )


def test_published_schema_self_contained() -> None:
    """M9 fix: every ``#/$defs/<name>`` reference must resolve."""
    schema = json.loads(SCHEMA_PATH.read_text())
    defs = schema.get("$defs", {}) or {}

    def _walk(obj: Any, seen_refs: set[str]) -> None:
        if isinstance(obj, dict):
            ref = obj.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/$defs/"):
                seen_refs.add(ref.split("/")[-1])
            for v in obj.values():
                _walk(v, seen_refs)
        elif isinstance(obj, list):
            for v in obj:
                _walk(v, seen_refs)

    seen: set[str] = set()
    _walk(schema, seen)
    missing = seen - set(defs.keys())
    assert not missing, (
        f"unresolved #/$defs refs in published schema: {sorted(missing)}"
    )


def test_schema_version_is_required_and_pattern() -> None:
    """C3 fix: schemaVersion is required and matches ``^\\d+-\\d+-\\d+$``."""
    schema = json.loads(SCHEMA_PATH.read_text())
    hdp = schema["$defs"]["HeritageDataPackage"]
    assert "schemaVersion" in hdp["required"]
    schemver = schema["$defs"].get(
        "SchemaVer", schema["$defs"]["HeritageDataPackage"]["$defs"].get("SchemaVer")
    )
    assert schemver is not None, "SchemaVer scalar missing from $defs"
    pattern = schemver["pattern"]
    # The stored value is a valid regex string (decoded from JSON-escaped
    # backslashes). Compile it and check that the canonical MODEL-REVISION-ADDITION
    # form validates; also accept any ``\d+-\d+-\d+`` shape.
    assert re.fullmatch(pattern, "1-0-0"), (
        f"SchemaVer pattern {pattern!r} does not accept '1-0-0'"
    )
    assert re.fullmatch(pattern, "99-12-34")
    assert not re.fullmatch(pattern, "1-0")  # too few parts
    assert not re.fullmatch(pattern, "abc-def-ghi")  # non-numeric


def test_confidence_bounded_0_to_1() -> None:
    """M8 fix: ProvenanceRecord.confidence is constrained to 0..1."""
    schema = json.loads(SCHEMA_PATH.read_text())
    prov = schema["$defs"]["ProvenanceRecord"]
    conf = prov["properties"]["confidence"]
    assert conf.get("minimum") == 0
    assert conf.get("maximum") == 1


# ── Round-trip structural tests ──────────────────────────────────────────


def _minimal_hdp() -> dict[str, Any]:
    """Build a JSON document that satisfies the 2.0 schema with the
    smallest possible payload."""
    return {
        "schemaVersion": "2-0-0",
        "createdAt": "2026-06-22T10:00:00Z",
        "contexts": [
            {
                "id": "11111111-2222-3333-4444-555555555555",
                "contextNumber": "[1001]",
                "unitType": "Deposit",
            }
        ],
        "relationships": [],
        "finds": [],
        "samples": [],
        "dates": [],
        "assets": [],
    }


def test_minimal_hdp_round_trip() -> None:
    """A minimal payload must validate and re-serialise identically."""
    payload = _minimal_hdp()
    pkg = HeritageDataPackage.model_validate(payload)
    dump = pkg.model_dump(mode="json")
    assert dump["schemaVersion"] == "2-0-0"
    assert len(dump["contexts"]) == 1
    assert dump["contexts"][0]["contextNumber"] == "[1001]"


def test_missing_schema_version_rejected() -> None:
    payload = _minimal_hdp()
    del payload["schemaVersion"]
    with pytest.raises(Exception) as exc_info:
        HeritageDataPackage.model_validate(payload)
    assert (
        "schemaVersion" in str(exc_info.value).lower()
        or "required" in str(exc_info.value).lower()
    )


def test_find_with_provenance_round_trip() -> None:
    payload = _minimal_hdp()
    payload["finds"] = [
        {
            "id": "11111111-2222-3333-4444-666666666666",
            "contextId": "11111111-2222-3333-4444-555555555555",
            "materialClass": "Pottery",
        }
    ]
    payload["provenanceLog"] = [
        {
            "entity": "11111111-2222-3333-4444-666666666666",
            "wasGeneratedBy": {
                "id": "11111111-2222-3333-4444-777777777777",
                "activityType": "SpeciesIdentification",
                "agent": {
                    "id": "11111111-2222-3333-4444-888888888888",
                    "agentType": "AIModel",
                    "name": "paleo-id-v1",
                    "modelId": "anthropic/claude",
                },
            },
            "generatedAtTime": "2026-06-22T11:00:00Z",
            "confidence": 0.85,
        }
    ]
    pkg = HeritageDataPackage.model_validate(payload)
    assert pkg.provenanceLog is not None
    assert pkg.provenanceLog[0].confidence == pytest.approx(0.85)
    assert pkg.provenanceLog[0].wasGeneratedBy is not None
    assert pkg.provenanceLog[0].wasGeneratedBy.agent.agentType.value == "AIModel"


def test_confidence_above_one_rejected() -> None:
    payload = _minimal_hdp()
    payload["provenanceLog"] = [
        {
            "entity": "11111111-2222-3333-4444-555555555555",
            "generatedAtTime": "2026-06-22T11:00:00Z",
            "confidence": 1.5,  # out of bounds
        }
    ]
    with pytest.raises(Exception):
        HeritageDataPackage.model_validate(payload)
