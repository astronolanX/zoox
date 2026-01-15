"""
Safety infrastructure - P0 critical guards for reef operations.

Components:
- guards: Pruning safeguards (deletion rate limits, protected scopes)
- audit: Audit trail for automatic operations
- undo: Undo buffer (quarantine) for deleted polips
"""

from .guards import PruningSafeguards, DryRunReport
from .audit import AuditLog, AuditEntry
from .undo import UndoBuffer

__all__ = [
    'PruningSafeguards',
    'DryRunReport',
    'AuditLog',
    'AuditEntry',
    'UndoBuffer',
]
