"""Platform-agnostic dynamic directory and path resolution module.

Provides canonical project root discovery and filesystem paths that work
seamlessly across Windows, macOS, Linux, Docker containers, and CI runners
regardless of the current working directory (cwd).
"""

import os
from pathlib import Path
from typing import Optional, Sequence, Union

# Root marker files or directories used to detect project boundary
ROOT_MARKERS: Sequence[str] = (
    "pyproject.toml",
    "docker-compose.yml",
    ".git",
    "Makefile",
)


def find_project_root(
    anchor: Optional[Union[str, Path]] = None,
    markers: Sequence[str] = ROOT_MARKERS,
) -> Path:
    """Dynamically discover project root by climbing parent directories.

    Prioritizes explicit environment variable CHURN_PROJECT_ROOT if defined.
    Otherwise climbs directory tree starting from the anchor (defaulting to this file)
    until a root marker is located.

    Args:
        anchor: Starting path or file to climb from.
        markers: Filenames or directory names that indicate repository root.

    Returns:
        Canonical resolved Path pointing to the project root.
    """
    env_root = os.getenv("CHURN_PROJECT_ROOT")
    if env_root:
        candidate = Path(env_root).resolve()
        if candidate.exists():
            return candidate

    current = Path(anchor).resolve() if anchor else Path(__file__).resolve()
    if current.is_file():
        current = current.parent

    # Traverse upward until reaching filesystem root
    for parent in [current] + list(current.parents):
        if any((parent / marker).exists() for marker in markers):
            return parent.resolve()

    # Fallback: assuming structure <root>/src/utils/paths.py
    return Path(__file__).resolve().parent.parent.parent


def ensure_dir(dir_path: Union[str, Path]) -> Path:
    """Create directory if it does not already exist and return resolved Path."""
    resolved = Path(dir_path).resolve()
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def resolve_path(path_input: Union[str, Path], base_dir: Optional[Path] = None) -> Path:
    """Resolve path input; anchors relative paths to project root or base_dir."""
    p = Path(path_input)
    if p.is_absolute():
        return p.resolve()
    base = base_dir or PROJECT_ROOT
    return (base / p).resolve()


# Canonical Project Root
PROJECT_ROOT: Path = find_project_root()

# Core Data Directories
DATA_DIR: Path = ensure_dir(PROJECT_ROOT / "data")
RAW_DATA_DIR: Path = ensure_dir(DATA_DIR / "raw")
PROCESSED_DATA_DIR: Path = ensure_dir(DATA_DIR / "processed")

# Model Storage
MODELS_DIR: Path = ensure_dir(PROJECT_ROOT / "models")
PROD_MODEL_PATH: Path = MODELS_DIR / "production_model.joblib"
CANDIDATE_MODEL_PATH: Path = MODELS_DIR / "candidate_model.joblib"

# Reports & Monitoring
REPORTS_DIR: Path = ensure_dir(PROJECT_ROOT / "reports")
DRIFT_REPORT_HTML_PATH: Path = REPORTS_DIR / "data_drift_report.html"
DRIFT_SUMMARY_JSON_PATH: Path = REPORTS_DIR / "drift_summary.json"

# Transformations & Orchestration
DBT_DIR: Path = PROJECT_ROOT / "dbt"
AIRFLOW_DIR: Path = PROJECT_ROOT / "airflow"
LOGS_DIR: Path = ensure_dir(PROJECT_ROOT / "logs")

# Default Dataset Cache
DEFAULT_RAW_DATA_PATH: Path = RAW_DATA_DIR / "telco_churn.csv"
