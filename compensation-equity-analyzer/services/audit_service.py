"""
Audit Service
Maintains immutable audit trails of all system modifications, access, and exceptions.
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from models.supporting import AuditLog

class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        entity_name: str,
        entity_id: str,
        action: str,
        actor_id: str,
        actor_role: str,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        severity: str = "INFO",
        ip_address: Optional[str] = "127.0.0.1"
    ) -> AuditLog:
        """
        Creates an immutable audit log entry.
        """
        audit_id = f"AUD-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}-{entity_id[:8]}"
        log_entry = AuditLog(
            id=audit_id,
            entity_name=entity_name,
            entity_id=entity_id,
            action=action,
            actor_id=actor_id,
            actor_role=actor_role,
            old_values=json.dumps(old_values, default=str) if old_values else None,
            new_values=json.dumps(new_values, default=str) if new_values else None,
            severity=severity,
            ip_address=ip_address,
            created_at=datetime.utcnow()
        )
        self.db.add(log_entry)
        self.db.commit()
        return log_entry
