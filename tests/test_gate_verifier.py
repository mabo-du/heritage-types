"""Local verifier for the publish-models.yml gate.

Mirrors the two bash gates inside ``.github/workflows/publish-models.yml``
in pure Python so the gate behaviour is exercisable without a real
GitHub run::

    # Gate A — workflow_dispatch acknowledgement substring
    ack_ok("I have notified the downstream maintainers")
    # Gate B — strict-major regex on tag push
    tag_rejected("models-v2.0.0")
    tag_accepted("models-v2.0.7")

These tests pin the gate semantics so a refactoring of the YAML does
not silently let a future major bump (``models-v11.0.0``,
``models-v100.0.0``) auto-publish through a tag push without the
operator having to use ``workflow_dispatch``.
"""

from __future__ import annotations

import re

import pytest

# Mirrors .github/workflows/publish-models.yml `Validate acknowledgement text` step.
REQUIRED_ACK_SUBSTRING = "I have notified the downstream maintainers"

# Mirrors .github/workflows/publish-models.yml `Reject tag-pushed strict-major bump`
# step. Anchored on both ends so intra-major patch bumps (e.g. ``models-v2.0.7``)
# flow through unhindered.
STRICT_MAJOR_RE = re.compile(r"^models-v[0-9]+\.0\.0$")


def ack_ok(text: str) -> bool:
    """Return True iff *text* contains the required acknowledgement substring."""
    return REQUIRED_ACK_SUBSTRING in text


def tag_rejected(tag: str) -> bool:
    """Return True iff *tag* matches the strict-major regex (would be rejected)."""
    return bool(STRICT_MAJOR_RE.match(tag))


# ── Tag-aware dispatch: which gate fires? ──────────────────────────────────


def gate_decision(
    event_name: str,
    ref_name: str | None = None,
    ack_text: str | None = None,
) -> tuple[str, str]:
    """Mimic the publish-models.yml gate logic and return (decision, reason).

    Decisions:
        "publish" — proceed to publish step
        "reject" — fail with the gate's error message
        "skip"   — outside the workflow's trigger surface (e.g. push to main)
    """
    if event_name == "workflow_dispatch":
        return (
            ("publish", "dispatch ack substring matched")
            if ack_ok(ack_text or "")
            else ("reject", "dispatch ack substring missing")
        )
    if event_name == "push" and ref_name:
        if tag_rejected(ref_name):
            return ("reject", f"strict-major bump {ref_name!r} requires dispatch")
        return ("publish", f"non-major bump {ref_name!r} flows through")
    return ("skip", f"event {event_name!r} not handled by publish gate")


# ── Strict-major regex behaviour ───────────────────────────────────────────


@pytest.mark.parametrize(
    "tag, should_reject",
    [
        # Strict-major bumps — REJECTED at the gate.
        ("models-v0.0.0", True),
        ("models-v1.0.0", True),
        ("models-v2.0.0", True),
        ("models-v3.0.0", True),
        ("models-v11.0.0", True),  # forward-compat: no more v0..v10 ceiling
        ("models-v100.0.0", True),
        # Intra-major patch bumps — ACCEPTED.
        ("models-v0.0.7", False),
        ("models-v1.5.0", False),
        ("models-v2.0.7", False),
        ("models-v2.3.4", False),
        ("models-v11.7.3", False),
        ("models-v100.99.99", False),
        # Non-models-v tags — out of scope, treated as not-rejected-by-this-gate.
        ("v1.0.0", False),
        ("release-v2.0.0", False),
    ],
)
def test_strict_major_regex(tag: str, should_reject: bool) -> None:
    assert tag_rejected(tag) is should_reject, (
        f"strict-major regex mismatch on {tag!r}: "
        f"expected rejected={should_reject}, got {tag_rejected(tag)}"
    )


# ── Dispatch acknowledgement behaviour ─────────────────────────────────────


@pytest.mark.parametrize(
    "ack, expected",
    [
        (
            "Per AGENTS.md, I have notified the downstream maintainers via "
            "GitHub issues in HOARD, StratiGraph and Trowel. Coordination "
            "cycle completed 2026-06-21.",
            True,
        ),
        ("i have notified the downstream maintainers", False),  # capitalisation matters
        ("I have notified downstream maintainers", False),  # missing "the"
        ("", False),
        # Exact phrase on its own line is sufficient.
        ("I have notified the downstream maintainers", True),
    ],
)
def test_ack_substring(ack: str, expected: bool) -> None:
    assert ack_ok(ack) is expected


# ── End-to-end gate decisions ──────────────────────────────────────────────


@pytest.mark.parametrize(
    "event_name, ref_name, ack_text, expected_decision, reason_fragment",
    [
        # Major-bump dispatch with full acknowledgement → publish.
        (
            "workflow_dispatch",
            None,
            "I have notified the downstream maintainers",
            "publish",
            "ack",
        ),
        # Major-bump dispatch without the literal phrase → reject.
        (
            "workflow_dispatch",
            None,
            "yes I notified them",
            "reject",
            "missing",
        ),
        # Strict-major bump tag-pushed → reject (must use dispatch).
        (
            "push",
            "models-v2.0.0",
            None,
            "reject",
            "strict-major",
        ),
        (
            "push",
            "models-v11.0.0",  # forward-compat: gate catches it
            None,
            "reject",
            "strict-major",
        ),
        # Intra-major patch bump tag-pushed → publish through gate.
        (
            "push",
            "models-v2.0.7",
            None,
            "publish",
            "non-major",
        ),
        # Push to a branch (not a tag) → skip (handled by other workflow).
        ("push", None, None, "skip", "not"),
    ],
)
def test_gate_decision(
    event_name: str,
    ref_name: str | None,
    ack_text: str | None,
    expected_decision: str,
    reason_fragment: str,
) -> None:
    decision, reason = gate_decision(event_name, ref_name, ack_text)
    assert decision == expected_decision
    assert reason_fragment.lower() in reason.lower(), (
        f"gate reason {reason!r} missing fragment {reason_fragment!r}"
    )


# ── Forward-compatibility: ages well forever ───────────────────────────────


@pytest.mark.parametrize("v", [11, 23, 42, 99, 100, 1000])
def test_strict_major_regex_catches_arbitrary_future_versions(v: int) -> None:
    """The gate must reject ``models-v{N}.0.0`` for any positive integer N.

    Backed by the positive anchored regex ``^models-v[0-9]+\\.0\\.0$`` —
    no v0..v10 ceiling like the buggy v1 implementation had.
    """
    tag = f"models-v{v}.0.0"
    assert tag_rejected(tag), f"future major {tag!r} bypassed the gate"


@pytest.mark.parametrize("v", [11, 23, 42, 99, 100, 1000])
def test_strict_major_regex_passes_arbitrary_future_patches(v: int) -> None:
    """For the same N, ``models-v{N}.0.7`` (intra-major patch) must pass."""
    tag = f"models-v{v}.0.7"
    assert not tag_rejected(tag), f"non-major patch {tag!r} erroneously rejected"
