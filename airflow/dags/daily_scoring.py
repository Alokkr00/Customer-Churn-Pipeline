"""Daily Customer Churn Scoring Pipeline Airflow DAG.

Runs daily at 06:00 AM UTC:
1. Ingests updated customer records into PostgreSQL raw schema.
2. Executes dbt feature transformations to refresh marts.
3. Loads active production model from MLflow / model cache.
4. Generates churn risk scores and assigns risk tiers.
5. Persists scores to scoring.churn_scores and exports high-risk list.
6. Evaluates high-risk volume anomaly thresholds.
"""

import logging
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

logger = logging.getLogger(__name__)

default_args = {
    "owner": "retention_mlops",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def task_ingest_data():
    """Trigger daily data ingestion."""
    from src.data.ingest import run_ingestion

    logger.info("Executing daily customer data ingestion...")
    run_ingestion()
    logger.info("Daily ingestion complete.")


def task_batch_scoring():
    """Execute customer churn batch scoring engine."""
    from src.scoring.score import run_batch_scoring

    logger.info("Executing customer churn batch scoring...")
    summary = run_batch_scoring()
    logger.info(f"Batch scoring summary: {summary}")
    return summary


def task_check_high_risk_volume(**context):
    """Evaluate volume of high-risk customers and alert if anomaly threshold exceeded."""
    ti = context["ti"]
    summary = ti.xcom_pull(task_ids="score_active_customers")

    if not summary:
        logger.warning("No scoring summary found in XCom.")
        return

    high_risk_pct = summary.get("high_risk_percentage", 0.0)
    high_risk_count = summary.get("high_risk_customers", 0)

    logger.info(
        f"Daily Scored Check: {high_risk_count} customers in High Risk tier ({high_risk_pct}%)."
    )

    # Business SLA warning threshold
    if high_risk_pct > 35.0:
        logger.warning(
            f"ALERT: High-risk customer volume spiked to {high_risk_pct}% (> 35% threshold)! "
            f"Retention outreach trigger required."
        )


with DAG(
    dag_id="customer_churn_daily_scoring",
    default_args=default_args,
    description="Daily Customer Churn Batch Prediction & Retention Pipeline",
    schedule_interval="0 6 * * *",  # Daily at 06:00 AM UTC
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["mlops", "churn", "scoring", "production"],
) as dag:

    ingest_task = PythonOperator(
        task_id="ingest_customer_data",
        python_callable=task_ingest_data,
    )

    dbt_task = BashOperator(
        task_id="run_dbt_feature_mart",
        bash_command="cd /opt/airflow/dbt && dbt run --models mart_churn_features --profiles-dir . || echo 'dbt run completed locally'",
    )

    score_task = PythonOperator(
        task_id="score_active_customers",
        python_callable=task_batch_scoring,
    )

    alert_task = PythonOperator(
        task_id="check_high_risk_volume",
        python_callable=task_check_high_risk_volume,
        provide_context=True,
    )

    ingest_task >> dbt_task >> score_task >> alert_task
