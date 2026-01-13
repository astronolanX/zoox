"""
zoox - Symbiotic memory for AI.

A reef is a colony of polyps.
"""

from zoox.blob import (
    Blob,
    BlobType,
    BlobScope,
    BlobStatus,
    Glob,
    BLOB_VERSION,
)
from zoox import cli

__all__ = [
    "Blob",
    "BlobType",
    "BlobScope",
    "BlobStatus",
    "Glob",
    "BLOB_VERSION",
    "cli",
]

__version__ = "0.1.0"
