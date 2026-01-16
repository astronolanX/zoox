"""
Reef filesystem structure constants.

Central source of truth for directory names, extensions, and lifecycle mappings.
"""

from pathlib import Path

# ============================================================================
# DIRECTORY STRUCTURE
# ============================================================================

# Main reef directory (was .claude)
REEF_DIR = ".reef"

# Subdirectories by lifecycle stage
SUBDIRS = {
    "current": "current",      # Active/living memory (*.reef)
    "bedrock": "bedrock",      # Immutable constraints (*.rock)
    "settled": "settled",      # Archived/decayed (*.sed)
    "pool": "pool",            # Admin tidal pool (*.reef) - bubble up to main
}

# Legacy directory (for migration)
LEGACY_DIR = ".claude"

# ============================================================================
# FILE EXTENSIONS
# ============================================================================

# Primary extensions by lifecycle
EXTENSIONS = {
    "living": ".reef",     # Active memory
    "immutable": ".rock",  # Bedrock constraints
    "settled": ".sed",     # Archived/decayed
}

# All recognized extensions (including legacy)
POLIP_EXTENSIONS = (".reef", ".rock", ".sed", ".blob.xml")

# Extension to lifecycle mapping
EXTENSION_LIFECYCLE = {
    ".reef": "living",
    ".rock": "immutable",
    ".sed": "settled",
    ".blob.xml": "living",  # Legacy treated as living
}

# Default extension for new polips
DEFAULT_EXTENSION = ".reef"

# ============================================================================
# TYPE TO SUBDIR/EXTENSION MAPPING
# ============================================================================

# Polip type → default subdirectory
TYPE_TO_SUBDIR = {
    "thread": "current",
    "decision": "current",
    "context": "current",
    "fact": "current",
    "constraint": "bedrock",
}

# Polip type → default extension
TYPE_TO_EXTENSION = {
    "thread": ".reef",
    "decision": ".reef",
    "context": ".reef",
    "fact": ".reef",
    "constraint": ".rock",
}

# ============================================================================
# TIDAL POOL (Admin/Dev Space)
# ============================================================================

# Tidal pool is a personal sandbox that can "bubble up" to main reef
POOL_SUBDIR = "pool"

# Commands for pool operations
POOL_COMMANDS = {
    "bubble": "Promote from pool to main reef",
    "drain": "Archive pool contents to settled",
}

# ============================================================================
# SPECIAL FILES
# ============================================================================

INDEX_FILE = "index.reef"
LOCK_FILE = ".cleanup.lock"
MARKER_FILE = ".last-cleanup"
DRIFT_CONFIG = "drift.reef"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_reef_dir(project_dir: Path) -> Path:
    """Get the reef directory for a project."""
    return project_dir / REEF_DIR


def get_legacy_dir(project_dir: Path) -> Path:
    """Get the legacy .claude directory for migration."""
    return project_dir / LEGACY_DIR


def get_subdir(project_dir: Path, subdir_key: str) -> Path:
    """Get a subdirectory path."""
    return get_reef_dir(project_dir) / SUBDIRS.get(subdir_key, subdir_key)


def extension_for_type(polip_type: str) -> str:
    """Get the default extension for a polip type."""
    return TYPE_TO_EXTENSION.get(polip_type, DEFAULT_EXTENSION)


def subdir_for_type(polip_type: str) -> str:
    """Get the default subdirectory for a polip type."""
    return TYPE_TO_SUBDIR.get(polip_type, "current")


def lifecycle_for_extension(ext: str) -> str:
    """Get the lifecycle stage for an extension."""
    return EXTENSION_LIFECYCLE.get(ext, "living")


def is_valid_extension(ext: str) -> bool:
    """Check if an extension is recognized."""
    return ext in POLIP_EXTENSIONS
