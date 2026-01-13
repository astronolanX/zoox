"""
zoox - Symbiotic memory for AI.

A reef is a colony of polyps.

Terminology:
    polyp       = individual memory unit (was: blob)
    reef        = project colony (was: glob)
    current     = active thread (flowing work)
    bedrock     = constraint (foundation)
    deposit     = decision (strategic choice)
    fossil      = fact (preserved knowledge)
    drift       = cross-project spread (coming soon)
    archipelago = global network (coming soon)

    zooxanthellae = context that feeds memory (the invisible engine)

Like coral biology: memory without context starves. Memory with rich context thrives.
"""

from zoox.blob import (
    Blob,
    BlobType,
    BlobScope,
    BlobStatus,
    Glob,
    BLOB_VERSION,
    KNOWN_SUBDIRS,
)
from zoox import cli

# Coral-branded type aliases (recommended API)
Polyp = Blob            # Individual memory unit
Reef = Glob             # Project colony
PolypType = BlobType    # Type enum
PolypScope = BlobScope  # Scope enum
PolypStatus = BlobStatus  # Status enum
POLYP_VERSION = BLOB_VERSION  # Schema version

__all__ = [
    # Coral API (recommended)
    "Polyp",
    "Reef",
    "PolypType",
    "PolypScope",
    "PolypStatus",
    "POLYP_VERSION",
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
