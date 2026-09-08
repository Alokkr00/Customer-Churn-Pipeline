"""Data and Prediction Drift Monitoring.

Generates drift reports comparing baseline reference distributions
against current inference or incoming batches.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

import numpy as np
import pandas as pd
from scipy import stats

from src.features.feature_engineering import TARGET_COLUMN
from src.training.train import load_training_data, train_test_split_dataset
from src.utils.paths import (
    DRIFT_REPORT_HTML_PATH,
    DRIFT_SUMMARY_JSON_PATH,
    REPORTS_DIR,
    resolve_path,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def calculate_feature_drift(
    reference: pd.Series, current: pd.Series, p_threshold: float = 0.05
) -> Dict[str, Any]:
    """Calculate statistical test for drift (KS-test for numeric, Chi2 for categorical)."""
    clean_ref = reference.dropna()
    clean_curr = current.dropna()

    if len(clean_ref) == 0 or len(clean_curr) == 0:
        return {"drift_detected": False, "p_value": 1.0, "stat": 0.0}

    # Numeric feature -> Kolmogorov-Smirnov test
    if pd.api.types.is_numeric_dtype(clean_ref):
        res = stats.ks_2samp(clean_ref, clean_curr)
        drift_detected = bool(res.pvalue < p_threshold)
        return {
            "drift_detected": drift_detected,
            "p_value": float(res.pvalue),
            "stat": float(res.statistic),
            "type": "ks_test",
        }
    else:
        # Categorical feature -> Chi-square or unique count similarity
        ref_freq = clean_ref.value_counts(normalize=True)
        curr_freq = clean_curr.value_counts(normalize=True)
        all_keys = list(set(ref_freq.index).union(set(curr_freq.index)))
        p = [ref_freq.get(k, 1e-4) for k in all_keys]
        q = [curr_freq.get(k, 1e-4) for k in all_keys]
        p = np.array(p) / sum(p)
        q = np.array(q) / sum(q)
        # Calculate PSI for categorical
        psi = float(np.sum((q - p) * np.log(q / p)))
        return {
            "drift_detected": bool(psi > 0.1),
            "psi": psi,
            "type": "categorical_psi",
        }


def run_drift_analysis(
    reference_df: pd.DataFrame = None,
    current_df: pd.DataFrame = None,
    output_html_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Analyze data drift across all available features and generate HTML report."""
    if reference_df is None or current_df is None:
        full_df = load_training_data()
        ref, curr = train_test_split_dataset(full_df, test_size=0.3, random_state=42)
    else:
        ref = reference_df
        curr = current_df

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_file = resolve_path(output_html_path) if output_html_path else DRIFT_REPORT_HTML_PATH

    # First attempt to use Evidently AI report
    try:
        from evidently.metric_preset import DataDriftPreset
        from evidently.report import Report

        logger.info("Generating Evidently AI Data Drift Report...")
        report = Report(metrics=[DataDriftPreset()])
        report.run(reference_data=ref, current_data=curr)
        report.save_html(str(report_file))
        logger.info(f"Evidently drift report saved to {report_file}")
    except Exception as exc:
        logger.warning(
            f"Evidently report generation skipped ({exc}). Generating standalone HTML report."
        )

    # Perform statistical tests across numeric features
    results = {}
    drifted_count = 0
    common_cols = [c for c in ref.columns if c in curr.columns and c != TARGET_COLUMN]

    for col in common_cols:
        col_res = calculate_feature_drift(ref[col], curr[col])
        results[col] = col_res
        if col_res["drift_detected"]:
            drifted_count += 1

    drift_share = drifted_count / max(1, len(common_cols))
    dataset_drift = drift_share >= 0.3

    summary = {
        "drift_detected": dataset_drift,
        "drifted_features_count": drifted_count,
        "total_features_evaluated": len(common_cols),
        "drift_share": round(drift_share, 4),
        "feature_details": results,
    }

    # Save summary as json report
    DRIFT_SUMMARY_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.Series(summary).to_json(DRIFT_SUMMARY_JSON_PATH, indent=2)
    logger.info(f"Drift summary saved to {DRIFT_SUMMARY_JSON_PATH}")

    return summary


if __name__ == "__main__":
    summary = run_drift_analysis()
    print("\n--- Drift Analysis Summary ---")
    print(f"Dataset Drift Detected: {summary['drift_detected']}")
    print(
        f"Drifted Features: {summary['drifted_features_count']} / {summary['total_features_evaluated']}"
    )
    print(f"Drift Share: {summary['drift_share']:.2%}")
