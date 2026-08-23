"""
OpenSight Enterprise - Alert & Notification Engine
Handles real-time alerting with deduplication, cooldowns, severity levels, and multiple channels.
"""
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import logging
import asyncio

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class AlertStatus(Enum):
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    ESCALATED = "escalated"

class Alert:
    def __init__(self, alert_id: str, event_type: str, camera_id: str, 
                 severity: AlertSeverity, message: str, metadata: Dict[str, Any] = None):
        self.alert_id = alert_id
        self.event_type = event_type
        self.camera_id = camera_id
        self.severity = severity
        self.message = message
        self.metadata = metadata or {}
        
        self.created_at = datetime.now()
        self.updated_at = self.created_at
        self.status = AlertStatus.NEW
        self.acknowledged_by: Optional[str] = None
        self.acknowledged_at: Optional[datetime] = None
        self.resolved_at: Optional[datetime] = None
        self.escalation_level = 0
        
        # Evidence references
        self.snapshot_url: Optional[str] = None
        self.clip_url: Optional[str] = None

    def acknowledge(self, user_id: str):
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_by = user_id
        self.acknowledged_at = datetime.now()
        self.updated_at = datetime.now()

    def resolve(self):
        self.status = AlertStatus.RESOLVED
        self.resolved_at = datetime.now()
        self.updated_at = datetime.now()

    def escalate(self):
        self.escalation_level += 1
        self.status = AlertStatus.ESCALATED
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "event_type": self.event_type,
            "camera_id": self.camera_id,
            "severity": self.severity.value,
            "message": self.message,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "escalation_level": self.escalation_level,
            "metadata": self.metadata,
            "snapshot_url": self.snapshot_url,
            "clip_url": self.clip_url
        }

class AlertEngine:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Alert storage
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        
        # Deduplication tracking: key -> last_alert_time
        self.dedup_cache: Dict[str, datetime] = {}
        
        # Cooldown periods (seconds) by severity
        self.cooldowns = {
            AlertSeverity.INFO: 300,      # 5 minutes
            AlertSeverity.WARNING: 120,   # 2 minutes
            AlertSeverity.CRITICAL: 60,   # 1 minute
            AlertSeverity.EMERGENCY: 30   # 30 seconds
        }
        
        # Notification handlers (callbacks)
        self.notification_handlers: List[Callable] = []
        
        # Rules engine: list of (condition_func, action_func)
        self.rules: List[tuple] = []
        
        # Stats
        self.stats = {
            "alerts_created": 0,
            "alerts_deduplicated": 0,
            "alerts_acknowledged": 0,
            "alerts_resolved": 0,
            "notifications_sent": 0
        }

    def add_notification_handler(self, handler: Callable):
        """Add a notification handler (email, webhook, websocket, etc.)."""
        self.notification_handlers.append(handler)

    def add_rule(self, condition: Callable, action: Callable):
        """Add an alerting rule."""
        self.rules.append((condition, action))

    def _generate_dedup_key(self, event_type: str, camera_id: str) -> str:
        return f"{event_type}:{camera_id}"

    def _is_cooldown(self, dedup_key: str, severity: AlertSeverity) -> bool:
        """Check if alert is in cooldown period."""
        if dedup_key not in self.dedup_cache:
            return False
            
        last_alert = self.dedup_cache[dedup_key]
        cooldown_period = self.cooldowns.get(severity, 120)
        
        return (datetime.now() - last_alert).total_seconds() < cooldown_period

    async def process_event(self, event: Dict[str, Any]) -> Optional[Alert]:
        """
        Process an incoming event and generate alert if conditions are met.
        
        Args:
            event: Event dictionary with type, camera_id, metadata, etc.
            
        Returns:
            Generated Alert or None if suppressed
        """
        event_type = event.get("type")
        camera_id = event.get("camera_id")
        severity_str = event.get("severity", "warning")
        message = event.get("message", f"Event detected: {event_type}")
        metadata = event.get("metadata", {})
        
        try:
            severity = AlertSeverity(severity_str)
        except ValueError:
            severity = AlertSeverity.WARNING
        
        dedup_key = self._generate_dedup_key(event_type, camera_id)
        
        # Check deduplication/cooldown
        if self._is_cooldown(dedup_key, severity):
            self.stats["alerts_deduplicated"] += 1
            logger.debug(f"Alert suppressed (cooldown): {dedup_key}")
            return None
        
        # Generate alert ID
        alert_id = f"{camera_id}_{event_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create alert
        alert = Alert(
            alert_id=alert_id,
            event_type=event_type,
            camera_id=camera_id,
            severity=severity,
            message=message,
            metadata=metadata
        )
        
        # Attach evidence URLs if available
        if "snapshot_id" in metadata:
            alert.snapshot_url = f"/api/v1/media/snapshots/{metadata['snapshot_id']}"
        if "clip_id" in metadata:
            alert.clip_url = f"/api/v1/media/clips/{metadata['clip_id']}"
        
        # Store alert
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        self.dedup_cache[dedup_key] = datetime.now()
        self.stats["alerts_created"] += 1
        
        logger.info(f"Alert created: {alert_id} - {message} [{severity.value}]")
        
        # Trigger notifications asynchronously
        await self._send_notifications(alert)
        
        # Evaluate rules for escalation/auto-actions
        await self._evaluate_rules(alert)
        
        return alert

    async def _send_notifications(self, alert: Alert):
        """Send notifications through all registered handlers."""
        for handler in self.notification_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
                self.stats["notifications_sent"] += 1
            except Exception as e:
                logger.error(f"Notification handler failed: {e}")

    async def _evaluate_rules(self, alert: Alert):
        """Evaluate alert against rules for auto-actions."""
        for condition, action in self.rules:
            try:
                if condition(alert):
                    await action(alert, self)
            except Exception as e:
                logger.error(f"Rule evaluation failed: {e}")

    def acknowledge_alert(self, alert_id: str, user_id: str) -> bool:
        """Acknowledge an alert."""
        if alert_id not in self.active_alerts:
            return False
            
        alert = self.active_alerts[alert_id]
        alert.acknowledge(user_id)
        self.stats["alerts_acknowledged"] += 1
        
        # Move from active to history if resolved
        if alert.status == AlertStatus.RESOLVED:
            del self.active_alerts[alert_id]
            
        return True

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        if alert_id not in self.active_alerts:
            return False
            
        alert = self.active_alerts[alert_id]
        alert.resolve()
        self.stats["alerts_resolved"] += 1
        del self.active_alerts[alert_id]
        
        return True

    def get_active_alerts(self, severity_filter: Optional[AlertSeverity] = None) -> List[Dict[str, Any]]:
        """Get all active alerts, optionally filtered by severity."""
        alerts = list(self.active_alerts.values())
        
        if severity_filter:
            alerts = [a for a in alerts if a.severity == severity_filter]
            
        # Sort by severity (emergency first) then by time
        severity_order = {
            AlertSeverity.EMERGENCY: 0,
            AlertSeverity.CRITICAL: 1,
            AlertSeverity.WARNING: 2,
            AlertSeverity.INFO: 3
        }
        alerts.sort(key=lambda a: (severity_order[a.severity], a.created_at))
        
        return [a.to_dict() for a in alerts]

    def get_stats(self) -> Dict[str, Any]:
        return self.stats.copy()


# Example notification handlers
async def email_notification_handler(alert: Alert):
    """Send email notification (placeholder)."""
    if alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY]:
        logger.info(f"[EMAIL] To: admin@example.com | Subject: {alert.severity.value.upper()}: {alert.event_type} | Body: {alert.message}")

async def webhook_notification_handler(alert: Alert):
    """Send webhook notification (placeholder)."""
    logger.info(f"[WEBHOOK] POST /alerts {alert.to_dict()}")

def websocket_broadcast_handler(alert: Alert):
    """Broadcast to connected WebSocket clients (placeholder)."""
    logger.info(f"[WEBSOCKET] Broadcasting alert {alert.alert_id} to {len([])} clients")
