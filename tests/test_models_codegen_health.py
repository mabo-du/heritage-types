"""Smoke guard for codegen drift.

`scripts/generate_python.py:_post_process_models` rewrites
``RootModel[UUID]`` → ``RootModel[str]`` (and the same for
``AwareDatetime``) so Pydantic accepts the ``Field(pattern=...)``
constraints. If the underlying ``datamodel-codegen`` or ``pydantic``
ever changes its emit shape, that regex silently misses and the
generated ``models.py`` ships with a constraint that Pydantic v2
rejects at import time — every consumer crashes on first install.

These tests pin the post-processed shape so a regression cannot
silently slip out of CI.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS_PATH = REPO_ROOT / "python" / "heritage_models" / "models.py"


@pytest.mark.skipif(not MODELS_PATH.exists(), reason="models.py not generated yet")
def test_no_rootmodel_uuid_in_models() -> None:
    text = MODELS_PATH.read_text()
    assert "RootModel[UUID]" not in text, (
        "codegen drift: 'RootModel[UUID]' reappeared in models.py. "
        "_post_process_models in scripts/generate_python.py likely stopped "
        "matching the new datamodel-codegen emit shape; update the regex "
        "or rewrite surgically. Without this guard, every consumer crashes "
        "at first import with 'Unable to apply constraint \"pattern\" to "
        "schema of type \"uuid\"'."
    )


@pytest.mark.skipif(not MODELS_PATH.exists(), reason="models.py not generated yet")
def test_no_rootmodel_aware_datetime_in_models() -> None:
    text = MODELS_PATH.read_text()
    assert "RootModel[AwareDatetime]" not in text, (
        "codegen drift: 'RootModel[AwareDatetime]' reappeared in models.py. "
        "Same root cause as the RootModel[UUID] drift above."
    )


@pytest.mark.skipif(not MODELS_PATH.exists(), reason="models.py not generated yet")
def test_heritage_data_package_is_base_model() -> None:
    """C1 regression guard: ``HeritageDataPackage`` is a ``BaseModel``,
    not the codegen-renamed ``HeritageDataPackage1`` shell."""
    text = MODELS_PATH.read_text()
    # Look for the canonical class declaration. ``class HeritageDataPackage(BaseModel)``
    # is the correct emitted line (post-fix). The legacy bug produced
    # ``class HeritageDataPackage(RootModel[Any])`` alongside a renamed
    # ``HeritageDataPackage1(BaseModel)``.
    assert "class HeritageDataPackage1" not in text, (
        "C1 regression: 'HeritageDataPackage1' (the codegen-renamed real "
        "model) is still present. Re-run `make all VERSION=1` after "
        "fixing scripts/generate_python.py."
    )
    assert "class HeritageDataPackage(BaseModel)" in text, (
        "C1 regression: 'HeritageDataPackage' is no longer a real BaseModel "
        "in the generated models.py. `--class-name HDP` in "
        "scripts/generate_python.py should ensure the canonical name is "
        "preserved."
    )
