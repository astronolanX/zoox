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
from reef.format import (
    POLIP_EPOCH,
    POLIP_SCHEMA,
    polip_version,
    parse_version,
    version_can_read,
    version_needs_migration,
    Polip as FormatPolip,
    Reef as FormatReef,
)
from reef import cli
from reef.calcification import (
    CalcificationEngine,
    AdversarialDecay,
    ReefHealth,
    DissolutionEngine,
    DecayStage,
)
from reef.importance import (
    ImportanceDetector,
    ImportanceScore,
    SignalType,
    score_importance,
)
from reef.observe import (
    ObservationExtractor,
    ConversationObserver,
    Observation,
    ObservationType,
    extract_observations,
    auto_observe,
)

# Coral-branded type aliases (recommended API)
Polip = Blob            # Individual memory unit (legacy XML-based)
Reef = Glob             # Project colony (legacy)
PolipType = BlobType    # Type enum
PolipScope = BlobScope  # Scope enum
PolipStatus = BlobStatus  # Status enum
POLIP_VERSION = BLOB_VERSION  # Legacy schema version (use polip_version() for new format)

__all__ = [
    # Coral API (recommended)
    "Polip",
    "Reef",
    "PolipType",
    "PolipScope",
    "PolipStatus",
    "POLIP_VERSION",
    # New versioning (EPOCH.SCHEMA)
    "POLIP_EPOCH",
    "POLIP_SCHEMA",
    "polip_version",
    "parse_version",
    "version_can_read",
    "version_needs_migration",
    "FormatPolip",
    "FormatReef",
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
    # Anti-git features
    "CalcificationEngine",
    "AdversarialDecay",
    "ReefHealth",
    "DissolutionEngine",
    "DecayStage",
    "ImportanceDetector",
    "ImportanceScore",
    "SignalType",
    "score_importance",
    "ObservationExtractor",
    "ConversationObserver",
    "Observation",
    "ObservationType",
    "extract_observations",
    "auto_observe",
]

__version__ = "0.1.0"
