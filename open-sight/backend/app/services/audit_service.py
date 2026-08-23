"""
Audit Service
Handles audit logging for compliance and security tracking.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Any
from uuid import UUID

from app.db import AsyncSessionLocal
from app.models.entities import AuditLog


logger = logging.getLogger(__name__)


class AuditService:
    """Service for audit trail management."""
    
    async def log_action(
        self,
        actor: str,
        action: str,
        resource: str,
        result: str,
        resource_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Log an audit action."""
        try:
            async with AsyncSessionLocal() as session:
                audit_log = AuditLog(
                    timestamp=datetime.now(timezone.utc),
                    username=actor,
                    action=action,
                    resource=resource,
                    resource_id=resource_id,
                    result=result,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details=details or {},
                )
                session.add(audit_log)
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to log audit action: {e}")
    
    async def get_logs(
        self,
        limit: int = 100,
        action: Optional[str] = None,
        resource: Optional[str] = None,
    ):
        """Retrieve audit logs with optional filters."""
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            
            query = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)
            
            if action:
                query = query.where(AuditLog.action == action)
            if resource:
                query = query.where(AuditLog.resource == resource)
            
            result = await session.execute(query)
            return list(result.scalars().all())
