"""Unit tests for high-risk volume anomaly spike alerts and webhooks."""

from unittest.mock import MagicMock, patch

from src.monitoring.alerts import send_spike_alert


def test_send_spike_alert_no_webhook(monkeypatch):
    """Ensure send_spike_alert gracefully skips if no webhook configured."""
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("ALERT_WEBHOOK_URL", raising=False)

    dispatched = send_spike_alert(
        high_risk_count=150,
        total_count=300,
        high_risk_pct=50.0,
        threshold_pct=35.0,
    )
    assert dispatched is False


def test_send_spike_alert_slack_success(monkeypatch):
    """Ensure send_spike_alert successfully posts to configured Slack webhook."""
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/test/mock/webhook")

    mock_resp = MagicMock()
    mock_resp.status = 200

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        dispatched = send_spike_alert(
            high_risk_count=200,
            total_count=500,
            high_risk_pct=40.0,
            threshold_pct=35.0,
        )
        assert dispatched is True
        assert mock_urlopen.called


def test_send_spike_alert_generic_webhook_success(monkeypatch):
    """Ensure send_spike_alert posts to generic ALERT_WEBHOOK_URL if Slack is absent."""
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    monkeypatch.setenv("ALERT_WEBHOOK_URL", "https://api.example.com/alerts/webhook")

    mock_resp = MagicMock()
    mock_resp.status = 200

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        dispatched = send_spike_alert(
            high_risk_count=180,
            total_count=400,
            high_risk_pct=45.0,
            threshold_pct=30.0,
            dashboard_url="http://retention.mycompany.internal",
        )
        assert dispatched is True
        assert mock_urlopen.called


def test_send_spike_alert_network_failure(monkeypatch):
    """Ensure network failure is caught and returns False without raising exception."""
    monkeypatch.setenv("ALERT_WEBHOOK_URL", "https://example.com/webhook")

    with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
        dispatched = send_spike_alert(
            high_risk_count=200,
            total_count=500,
            high_risk_pct=40.0,
            threshold_pct=35.0,
        )
        assert dispatched is False
