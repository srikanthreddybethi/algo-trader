"""
Alerting System — monitors all system failures and sends notifications.

Severity levels:
  CRITICAL: System cannot trade (exchange down, kill switch, liquidation risk)
  HIGH:     Trade failed, AI unavailable, significant losses
  MEDIUM:   Strategy errors, data stale, rate limits hit
  LOW:      Config changes, minor warnings, informational

Notification plugins:
  - In-app (always on) — stored in database and shown in UI
  - Email (SMTP) — optional, configured via env vars
  - Webhook (Slack/Discord/Telegram) — optional, any URL
  - Console log (always on) — for server monitoring
"""
import asyncio
import logging
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from collections import defaultdict

import httpx

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# SEVERITY LEVELS
# ═══════════════════════════════════════════════════════════════
class Severity:
    CRITICAL = "critical"  # System cannot function
    HIGH = "high"          # Major issue, needs attention
    MEDIUM = "medium"      # Notable issue, monitor
    LOW = "low"            # Informational


# ═══════════════════════════════════════════════════════════════
# ALERT CATEGORIES
# ═══════════════════════════════════════════════════════════════
ALERT_CATEGORIES = {
    # Exchange failures
    "exchange_connection_failed": Severity.CRITICAL,
    "exchange_order_rejected": Severity.HIGH,
    "exchange_rate_limited": Severity.MEDIUM,
    "exchange_timeout": Severity.HIGH,

    # AI/External service failures
    "ai_api_failed": Severity.MEDIUM,
    "ai_api_key_missing": Severity.LOW,
    "ai_api_rate_limited": Severity.MEDIUM,
    "news_feed_failed": Severity.LOW,
    "coingecko_api_failed": Severity.LOW,
    "fear_greed_api_failed": Severity.LOW,

    # Trading failures
    "trade_execution_failed": Severity.HIGH,
    "order_rejected_insufficient_funds": Severity.HIGH,
    "order_rejected_min_size": Severity.MEDIUM,
    "liquidation_warning": Severity.CRITICAL,
    "circuit_breaker_triggered": Severity.CRITICAL,

    # Risk events
    "max_drawdown_breached": Severity.CRITICAL,
    "kill_switch_activated": Severity.CRITICAL,
    "losing_streak_detected": Severity.HIGH,
    "daily_loss_limit_hit": Severity.HIGH,
    "extreme_sentiment": Severity.MEDIUM,

    # Performance alerts
    "strategy_underperforming": Severity.MEDIUM,
    "no_trades_24h": Severity.LOW,
    "portfolio_new_high": Severity.LOW,
    "portfolio_new_low": Severity.HIGH,

    # System health
    "database_error": Severity.CRITICAL,
    "memory_persistence_failed": Severity.MEDIUM,
    "cycle_error": Severity.HIGH,
    "startup_complete": Severity.LOW,
    "config_changed": Severity.LOW,
}


# ═══════════════════════════════════════════════════════════════
# NOTIFICATION PLUGINS
# ═══════════════════════════════════════════════════════════════
class NotificationPlugin:
    """Base class for notification delivery."""
    name: str = "base"
    min_severity: str = Severity.LOW  # Only send alerts at or above this level

    async def send(self, alert: Dict) -> bool:
        raise NotImplementedError


class ConsolePlugin(NotificationPlugin):
    """Always-on console logging."""
    name = "console"

    async def send(self, alert: Dict) -> bool:
        severity = alert["severity"]
        emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}.get(severity, "⚪")
        logger.warning(f"{emoji} ALERT [{severity.upper()}] {alert['category']}: {alert['message']}")
        return True


class EmailPlugin(NotificationPlugin):
    """Send alerts via SMTP email."""
    name = "email"
    min_severity = Severity.HIGH  # Only email for HIGH and CRITICAL

    def __init__(self):
        self.smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        self.smtp_user = os.environ.get("SMTP_USER", "")
        self.smtp_pass = os.environ.get("SMTP_PASS", "")
        self.from_email = os.environ.get("ALERT_FROM_EMAIL", self.smtp_user)
        self.to_email = os.environ.get("ALERT_TO_EMAIL", "")

    @property
    def is_configured(self) -> bool:
        return bool(self.smtp_user and self.smtp_pass and self.to_email)

    async def send(self, alert: Dict) -> bool:
        if not self.is_configured:
            return False

        try:
            msg = MIMEMultipart()
            msg["From"] = self.from_email
            msg["To"] = self.to_email
            msg["Subject"] = f"[AlgoTrader {alert['severity'].upper()}] {alert['category']}"

            body = f"""
AlgoTrader Alert
================
Severity: {alert['severity'].upper()}
Category: {alert['category']}
Time: {alert['timestamp']}

Message: {alert['message']}

Details: {json.dumps(alert.get('details', {}), indent=2)}
"""
            msg.attach(MIMEText(body, "plain"))

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._send_smtp, msg)
            return True
        except Exception as e:
            logger.error(f"Email alert failed: {e}")
            return False

    def _send_smtp(self, msg):
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_pass)
            server.send_message(msg)


class WebhookPlugin(NotificationPlugin):
    """Send alerts to any webhook URL (Slack, Discord, Telegram, etc.)."""
    name = "webhook"
    min_severity = Severity.MEDIUM

    def __init__(self):
        self.webhook_url = os.environ.get("ALERT_WEBHOOK_URL", "")

    @property
    def is_configured(self) -> bool:
        return bool(self.webhook_url)

    async def send(self, alert: Dict) -> bool:
        if not self.is_configured:
            return False

        try:
            severity = alert["severity"]
            emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}.get(severity, "⚪")

            # Format for Slack/Discord/generic webhook
            payload = {
                "text": f"{emoji} *AlgoTrader [{severity.upper()}]*\n`{alert['category']}`\n{alert['message']}",
                # Discord format
                "content": f"{emoji} **AlgoTrader [{severity.upper()}]**\n`{alert['category']}`\n{alert['message']}",
            }

            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(self.webhook_url, json=payload)
            return True
        except Exception as e:
            logger.error(f"Webhook alert failed: {e}")
            return False


# ═══════════════════════════════════════════════════════════════
# IN-APP ALERT STORE
# ═══════════════════════════════════════════════════════════════
class InAppPlugin(NotificationPlugin):
    """Stores alerts for the UI to display."""
    name = "in_app"

    def __init__(self):
        self._alerts: List[Dict] = []
        self._max_alerts = 500

    async def send(self, alert: Dict) -> bool:
        self._alerts.insert(0, alert)
        if len(self._alerts) > self._max_alerts:
            self._alerts = self._alerts[:self._max_alerts]
        return True

    def get_alerts(self, limit: int = 50, severity: Optional[str] = None,
                    category: Optional[str] = None, unread_only: bool = False) -> List[Dict]:
        alerts = self._alerts
        if severity:
            sev_order = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]
            min_idx = sev_order.index(severity) if severity in sev_order else 3
            allowed = set(sev_order[:min_idx + 1])
            alerts = [a for a in alerts if a["severity"] in allowed]
        if category:
            alerts = [a for a in alerts if a["category"] == category]
        if unread_only:
            alerts = [a for a in alerts if not a.get("read")]
        return alerts[:limit]

    def mark_read(self, alert_id: str):
        for a in self._alerts:
            if a.get("id") == alert_id:
                a["read"] = True
                break

    def get_unread_count(self) -> Dict:
        counts = defaultdict(int)
        for a in self._alerts:
            if not a.get("read"):
                counts[a["severity"]] += 1
        return dict(counts)

    def clear(self, severity: Optional[str] = None):
        if severity:
            self._alerts = [a for a in self._alerts if a["severity"] != severity]
        else:
            self._alerts.clear()


# ═══════════════════════════════════════════════════════════════
# ALERT RATE LIMITER (prevent spam)
# ═══════════════════════════════════════════════════════════════
class AlertRateLimiter:
    """Prevents the same alert from firing repeatedly."""

    def __init__(self, cooldown_seconds: int = 300):
        self._last_fired: Dict[str, datetime] = {}
        self.cooldown = timedelta(seconds=cooldown_seconds)

    def can_fire(self, category: str) -> bool:
        now = datetime.utcnow()
        if category in self._last_fired:
            if now - self._last_fired[category] < self.cooldown:
                return False
        self._last_fired[category] = now
        return True


# ═══════════════════════════════════════════════════════════════
# ALERT MANAGER (main orchestrator)
# ═══════════════════════════════════════════════════════════════
class AlertManager:
    """Central alert management — routes alerts to configured plugins."""

    def __init__(self):
        self.in_app = InAppPlugin()
        self.console = ConsolePlugin()
        self.email = EmailPlugin()
        self.webhook = WebhookPlugin()
        self.rate_limiter = AlertRateLimiter(cooldown_seconds=300)

        self._plugins: List[NotificationPlugin] = [
            self.in_app,
            self.console,
            self.email,
            self.webhook,
        ]

        self._alert_counter = 0
        self._stats: Dict[str, int] = defaultdict(int)

    async def fire(self, category: str, message: str, details: Optional[Dict] = None,
                    severity: Optional[str] = None):
        """Fire an alert through all configured plugins."""
        # Auto-determine severity if not provided
        if severity is None:
            severity = ALERT_CATEGORIES.get(category, Severity.MEDIUM)

        # Rate limit check (except CRITICAL — always fires)
        if severity != Severity.CRITICAL and not self.rate_limiter.can_fire(category):
            return

        self._alert_counter += 1
        self._stats[severity] += 1

        alert = {
            "id": f"alert_{self._alert_counter}_{int(datetime.utcnow().timestamp())}",
            "severity": severity,
            "category": category,
            "message": message,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat(),
            "read": False,
        }

        # Route to all plugins
        severity_order = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
        alert_level = severity_order.index(severity) if severity in severity_order else 0

        for plugin in self._plugins:
            try:
                min_level = severity_order.index(plugin.min_severity) if plugin.min_severity in severity_order else 0
                if alert_level >= min_level:
                    await plugin.send(alert)
            except Exception as e:
                logger.error(f"Alert plugin {plugin.name} failed: {e}")

    def get_alerts(self, **kwargs) -> List[Dict]:
        return self.in_app.get_alerts(**kwargs)

    def get_unread_count(self) -> Dict:
        return self.in_app.get_unread_count()

    def mark_read(self, alert_id: str):
        self.in_app.mark_read(alert_id)

    def clear(self, severity: Optional[str] = None):
        self.in_app.clear(severity)

    def get_stats(self) -> Dict:
        return {
            "total_alerts": self._alert_counter,
            "by_severity": dict(self._stats),
            "unread": self.in_app.get_unread_count(),
            "plugins": {
                "email": {"configured": self.email.is_configured, "min_severity": self.email.min_severity},
                "webhook": {"configured": self.webhook.is_configured, "min_severity": self.webhook.min_severity},
                "in_app": {"configured": True, "min_severity": "low"},
                "console": {"configured": True, "min_severity": "low"},
            },
            "rate_limit_seconds": self.rate_limiter.cooldown.seconds,
        }

    def get_config(self) -> Dict:
        return {
            "email_configured": self.email.is_configured,
            "email_to": self.email.to_email if self.email.is_configured else None,
            "webhook_configured": self.webhook.is_configured,
            "webhook_url": self.webhook.webhook_url[:30] + "..." if self.webhook.is_configured else None,
        }


# Singleton
alert_manager = AlertManager()
