"""
Goopy - XML blob system for Claude Code session memory.

A glob is a collection of blobs.
"""

from goopy.blob import (
    Blob,
    BlobType,
    BlobScope,
    BlobStatus,
    Glob,
    BLOB_VERSION,
)
from goopy import cli

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
