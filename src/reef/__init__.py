"""
reef - Symbiotic memory for AI.

A reef is a colony of polips.

Terminology:
    polip       = individual memory unit (was: blob)
    reef        = project colony (was: glob)
    current     = active thread (flowing work)
    bedrock     = constraint (foundation)
    deposit     = decision (strategic choice)
    fossil      = fact (preserved knowledge)
    drift       = cross-project spread (coming soon)
    archipelago = global network (coming soon)

    reefanthellae = context that feeds memory (the invisible engine)

Like coral biology: memory without context starves. Memory with rich context thrives.
"""

from reef.blob import (
    Blob,
    BlobType,
    BlobScope,
    BlobStatus,
    Glob,
    BLOB_VERSION,
    KNOWN_SUBDIRS,
)
from reef import cli

# Coral-branded type aliases (recommended API)
Polip = Blob            # Individual memory unit
Reef = Glob             # Project colony
PolipType = BlobType    # Type enum
PolipScope = BlobScope  # Scope enum
PolipStatus = BlobStatus  # Status enum
POLIP_VERSION = BLOB_VERSION  # Schema version

__all__ = [
    # Coral API (recommended)
    "Polip",
    "Reef",
    "PolipType",
    "PolipScope",
    "PolipStatus",
    "POLIP_VERSION",
    # Legacy API (backward compatible)
    "Blob",
    "BlobType",
    "BlobScope",
    "BlobStatus",
    "Glob",
    "BLOB_VERSION",
    "KNOWN_SUBDIRS",
    # Module
    "cli",
]

__version__ = "0.1.0"
