"""Anomaly detection alerts and webhook notifications module."""

import json
import logging
import os
import urllib.request
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


def send_spike_alert(
    high_risk_count: int,
    total_count: int,
    high_risk_pct: float,
    threshold_pct: float = 35.0,
    slack_webhook: Optional[str] = None,
    alert_webhook: Optional[str] = None,
    dashboard_url: Optional[str] = None,
) -> bool:
    """Send alert notification via Slack Webhook or generic HTTP Webhook.

    Returns True if an alert was dispatched, False otherwise.
    Never raises an unhandled exception to prevent breaking the caller pipeline.
    """
    # Attempt to read Airflow Variables if available in runtime context
    if not slack_webhook or not alert_webhook or not dashboard_url:
        try:
            from airflow.models import Variable

            slack_webhook = slack_webhook or Variable.get("SLACK_WEBHOOK_URL", default_var="")
            alert_webhook = alert_webhook or Variable.get("ALERT_WEBHOOK_URL", default_var="")
            dashboard_url = dashboard_url or Variable.get(
                "DASHBOARD_URL", default_var="http://localhost:8501"
            )
        except Exception:
            pass

    slack_webhook = slack_webhook or os.getenv("SLACK_WEBHOOK_URL", "")
    alert_webhook = alert_webhook or os.getenv("ALERT_WEBHOOK_URL", "")
    dashboard_url = dashboard_url or os.getenv("DASHBOARD_URL", "http://localhost:8501")

    if not slack_webhook and not alert_webhook:
        logger.info(
            "Neither SLACK_WEBHOOK_URL nor ALERT_WEBHOOK_URL is configured. "
            "Skipping external notification dispatch."
        )
        return False

    payload = {
        "text": f"🚨 High-Risk Customer Spike Alert: {high_risk_pct:.1f}% of active accounts flagged.",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🚨 High-Risk Customer Spike Detected",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*High-Risk Volume:*\n{high_risk_count} / {total_count} customers",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Risk Concentration:*\n`{high_risk_pct:.2f}%` (SLA Limit: {threshold_pct}%)",
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Severity:*\nCRITICAL RETENTION ACTION",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Scoring Timestamp:*\n{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
                    },
                ],
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Open Retention Dashboard",
                            "emoji": True,
                        },
                        "url": dashboard_url,
                        "style": "danger",
                    }
                ],
            },
        ],
    }

    target_url = slack_webhook or alert_webhook
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            target_url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "CustomerChurnPipeline/1.0"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.info(
                f"High-risk alert successfully dispatched to webhook (status {resp.status})."
            )
            return True
    except Exception as exc:
        logger.error(f"Failed to deliver high-risk webhook alert: {exc}")
        return False
