"""Unit tests for platform-agnostic dynamic path resolution."""

import os
from pathlib import Path

from src.utils.paths import (
    CANDIDATE_MODEL_PATH,
    DATA_DIR,
    DEFAULT_RAW_DATA_PATH,
    DRIFT_REPORT_HTML_PATH,
    DRIFT_SUMMARY_JSON_PATH,
    MODELS_DIR,
    PROD_MODEL_PATH,
    PROJECT_ROOT,
    RAW_DATA_DIR,
    REPORTS_DIR,
    ensure_dir,
    find_project_root,
    resolve_path,
)


def test_project_root_discovery():
    """Verify that find_project_root returns a valid directory with project markers."""
    root = find_project_root()
    assert isinstance(root, Path)
    assert root.is_absolute()
    assert root.exists()
    # Should contain project markers
    has_marker = any((root / m).exists() for m in ("pyproject.toml", "docker-compose.yml", "Makefile"))
    assert has_marker is True


def test_subdirectories_anchored_to_root():
    """Verify all standard directories are resolved relative to PROJECT_ROOT."""
    assert DATA_DIR.is_absolute()
    assert DATA_DIR.parent == PROJECT_ROOT
    assert RAW_DATA_DIR.parent == DATA_DIR
    assert MODELS_DIR.parent == PROJECT_ROOT
    assert REPORTS_DIR.parent == PROJECT_ROOT

    assert PROD_MODEL_PATH.parent == MODELS_DIR
    assert CANDIDATE_MODEL_PATH.parent == MODELS_DIR
    assert DRIFT_REPORT_HTML_PATH.parent == REPORTS_DIR
    assert DRIFT_SUMMARY_JSON_PATH.parent == REPORTS_DIR
    assert DEFAULT_RAW_DATA_PATH.parent == RAW_DATA_DIR


def test_resolve_path_relative_and_absolute():
    """Verify resolve_path handles both relative strings and absolute paths."""
    rel_path = "data/raw/custom.csv"
    resolved = resolve_path(rel_path)
    assert resolved.is_absolute()
    assert resolved == (PROJECT_ROOT / "data" / "raw" / "custom.csv").resolve()

    # Absolute path should remain unchanged
    abs_path = Path(os.getcwd()).resolve()
    assert resolve_path(abs_path) == abs_path


def test_env_var_root_override(tmp_path: Path, monkeypatch):
    """Verify CHURN_PROJECT_ROOT environment variable overrides default search."""
    fake_root = tmp_path / "custom_pipeline_root"
    fake_root.mkdir()
    (fake_root / "pyproject.toml").touch()

    monkeypatch.setenv("CHURN_PROJECT_ROOT", str(fake_root))
    discovered = find_project_root()
    assert discovered == fake_root.resolve()


def test_ensure_dir(tmp_path: Path):
    """Verify ensure_dir creates nested directories idempotently."""
    nested = tmp_path / "a" / "b" / "c"
    assert not nested.exists()
    result = ensure_dir(nested)
    assert result.exists()
    assert result.is_dir()
