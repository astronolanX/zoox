"""
Semantic PII Detection for Mediator SDK

Addresses Karen's identified attack vectors:
- Contextual/semantic PII (relationships, locations, schedules)
- Phonetic encoding ("five five five...")
- Fragmented disclosure across multiple messages
- Embedded in documents (OCR'd PDFs, screenshots)
- Deanonymizing nicknames ("Little Joey")
- Metadata PII (timestamps revealing schedules)

Design principles:
- Haiku for speed (<500ms latency target)
- Cross-message state for fragmented disclosure
- Content-addressable caching to avoid re-scanning
- Layered detection: regex first, semantic second
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Protocol
from collections import defaultdict


# =============================================================================
# Types and Protocols
# =============================================================================


class PIICategory(Enum):
    """PII categories with risk levels."""

    # Direct identifiers (critical)
    SSN = "ssn"
    PHONE = "phone"
    EMAIL = "email"
    ADDRESS = "address"
    DOB = "dob"
    FINANCIAL = "financial"

    # Semantic identifiers (high risk - Karen's focus)
    LOCATION_CONTEXTUAL = "location_contextual"  # "blue house on Maple, third from corner"
    RELATIONSHIP = "relationship"  # Names + relationships that deanonymize
    SCHEDULE = "schedule"  # Patterns revealing work/custody schedules
    MINOR_IDENTIFIER = "minor_identifier"  # Any info identifying children

    # Quasi-identifiers (medium risk)
    EMPLOYER = "employer"
    SCHOOL = "school"
    MEDICAL = "medical"
    VEHICLE = "vehicle"

    # Metadata (low-medium risk)
    TIMESTAMP_PATTERN = "timestamp_pattern"  # Reveals habits
    GEOLOCATION = "geolocation"

    # Reconstruction risk
    FRAGMENTED = "fragmented"  # Partial info that could combine


class PIISeverity(Enum):
    """Severity levels for detected PII."""
    CRITICAL = "critical"  # Block immediately
    HIGH = "high"  # Warn, require confirmation
    MEDIUM = "medium"  # Log, allow with notice
    LOW = "low"  # Log only


@dataclass
class PIIMatch:
    """A single PII detection result."""
    category: PIICategory
    severity: PIISeverity
    content: str  # The matched content
    start: int  # Start position in original text
    end: int  # End position
    confidence: float  # 0.0 - 1.0
    reasoning: str  # Why this was flagged
    redacted: str  # Suggested redaction

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "content": self.content,
            "start": self.start,
            "end": self.end,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "redacted": self.redacted,
        }


@dataclass
class PIIAnalysis:
    """Complete PII analysis result for a message."""
    message_id: str
    timestamp: datetime
    matches: list[PIIMatch]
    safe: bool  # True if no blocking PII found
    redacted_text: str | None  # Text with PII redacted
    risk_score: float  # 0.0 - 1.0 overall risk
    latency_ms: float  # Processing time

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "timestamp": self.timestamp.isoformat(),
            "matches": [m.to_dict() for m in self.matches],
            "safe": self.safe,
            "redacted_text": self.redacted_text,
            "risk_score": self.risk_score,
            "latency_ms": self.latency_ms,
        }


@dataclass
class FragmentedPIIState:
    """Tracks potential fragmented disclosure across messages."""
    session_id: str
    fragments: dict[PIICategory, list[tuple[str, datetime, str]]] = field(
        default_factory=lambda: defaultdict(list)
    )  # category -> [(content, timestamp, message_id), ...]

    potential_ssn_digits: list[tuple[str, datetime, str]] = field(default_factory=list)
    potential_phone_digits: list[tuple[str, datetime, str]] = field(default_factory=list)
    mentioned_names: set[str] = field(default_factory=set)
    mentioned_locations: list[str] = field(default_factory=list)

    def add_fragment(
        self,
        category: PIICategory,
        content: str,
        timestamp: datetime,
        message_id: str
    ) -> None:
        """Add a potential PII fragment."""
        self.fragments[category].append((content, timestamp, message_id))

        # Special handling for digit sequences (SSN, phone fragmentation)
        digits = re.sub(r'\D', '', content)
        if digits and len(digits) <= 4:
            if category == PIICategory.SSN:
                self.potential_ssn_digits.append((digits, timestamp, message_id))
            elif category == PIICategory.PHONE:
                self.potential_phone_digits.append((digits, timestamp, message_id))

    def check_reconstruction(self, window_hours: int = 4) -> list[PIIMatch]:
        """Check if fragments can reconstruct PII within time window."""
        cutoff = datetime.now() - timedelta(hours=window_hours)
        matches = []

        # Check SSN reconstruction (9 digits across messages)
        recent_ssn = [d for d, t, _ in self.potential_ssn_digits if t > cutoff]
        total_ssn_digits = ''.join(recent_ssn)
        if len(total_ssn_digits) >= 9:
            matches.append(PIIMatch(
                category=PIICategory.FRAGMENTED,
                severity=PIISeverity.CRITICAL,
                content=f"SSN reconstructable from {len(recent_ssn)} fragments",
                start=0,
                end=0,
                confidence=0.85,
                reasoning=f"Detected {len(recent_ssn)} numeric fragments across messages that could form SSN",
                redacted="[SSN FRAGMENTS DETECTED]"
            ))

        # Check phone reconstruction (10 digits)
        recent_phone = [d for d, t, _ in self.potential_phone_digits if t > cutoff]
        total_phone_digits = ''.join(recent_phone)
        if len(total_phone_digits) >= 10:
            matches.append(PIIMatch(
                category=PIICategory.FRAGMENTED,
                severity=PIISeverity.HIGH,
                content=f"Phone reconstructable from {len(recent_phone)} fragments",
                start=0,
                end=0,
                confidence=0.8,
                reasoning=f"Detected {len(recent_phone)} numeric fragments that could form phone number",
                redacted="[PHONE FRAGMENTS DETECTED]"
            ))

        return matches

    def prune_old(self, hours: int = 8) -> None:
        """Remove fragments older than window."""
        cutoff = datetime.now() - timedelta(hours=hours)

        for category in list(self.fragments.keys()):
            self.fragments[category] = [
                (c, t, m) for c, t, m in self.fragments[category] if t > cutoff
            ]

        self.potential_ssn_digits = [
            (d, t, m) for d, t, m in self.potential_ssn_digits if t > cutoff
        ]
        self.potential_phone_digits = [
            (d, t, m) for d, t, m in self.potential_phone_digits if t > cutoff
        ]


class LLMClient(Protocol):
    """Protocol for LLM client (Haiku)."""
    async def complete(self, prompt: str) -> str:
        """Get completion from LLM."""
        ...


# =============================================================================
# Regex-Based Detection (Layer 1 - Fast)
# =============================================================================


class RegexPIIDetector:
    """Fast regex-based PII detection. First layer before semantic analysis."""

    # Standard patterns
    PATTERNS: dict[PIICategory, list[tuple[re.Pattern, PIISeverity]]] = {
        PIICategory.SSN: [
            (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), PIISeverity.CRITICAL),
            (re.compile(r'\b\d{3}\s*\d{2}\s*\d{4}\b'), PIISeverity.CRITICAL),
        ],
        PIICategory.PHONE: [
            (re.compile(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b'), PIISeverity.HIGH),
            (re.compile(r'\(\d{3}\)\s*\d{3}[-.\s]?\d{4}'), PIISeverity.HIGH),
        ],
        PIICategory.EMAIL: [
            (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), PIISeverity.HIGH),
        ],
        PIICategory.DOB: [
            (re.compile(r'\b\d{1,2}/\d{1,2}/\d{2,4}\b'), PIISeverity.MEDIUM),
            (re.compile(r'\b\d{4}-\d{2}-\d{2}\b'), PIISeverity.MEDIUM),
        ],
        PIICategory.ADDRESS: [
            (re.compile(r'\b\d+\s+\w+\s+(street|st|avenue|ave|road|rd|drive|dr|lane|ln|court|ct|way|blvd|boulevard)\b', re.I), PIISeverity.HIGH),
        ],
        PIICategory.FINANCIAL: [
            (re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'), PIISeverity.CRITICAL),  # Credit card
            (re.compile(r'\baccount\s*#?\s*\d{6,}\b', re.I), PIISeverity.HIGH),
        ],
    }

    # Phonetic number patterns (Karen's attack vector)
    PHONETIC_DIGITS = {
        'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
        'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
        'oh': '0', 'o': '0',
    }

    # Number words
    NUMBER_WORDS = {
        'ten': '10', 'eleven': '11', 'twelve': '12', 'thirteen': '13',
        'fourteen': '14', 'fifteen': '15', 'sixteen': '16', 'seventeen': '17',
        'eighteen': '18', 'nineteen': '19', 'twenty': '20', 'thirty': '30',
        'forty': '40', 'fifty': '50', 'sixty': '60', 'seventy': '70',
        'eighty': '80', 'ninety': '90', 'hundred': '00',
    }

    def detect(self, text: str) -> list[PIIMatch]:
        """Run regex detection on text."""
        matches = []

        # Standard patterns
        for category, patterns in self.PATTERNS.items():
            for pattern, severity in patterns:
                for match in pattern.finditer(text):
                    matches.append(PIIMatch(
                        category=category,
                        severity=severity,
                        content=match.group(),
                        start=match.start(),
                        end=match.end(),
                        confidence=0.95,  # High confidence for regex
                        reasoning=f"Matched {category.value} pattern",
                        redacted=f"[{category.value.upper()}]"
                    ))

        # Phonetic detection
        phonetic_matches = self._detect_phonetic(text)
        matches.extend(phonetic_matches)

        return matches

    def _detect_phonetic(self, text: str) -> list[PIIMatch]:
        """Detect phonetically encoded numbers."""
        matches = []
        lower = text.lower()

        # Pattern for "my social is five five five twelve thirty-four fifty-six"
        # or "five five five, twelve, thirty-four fifty-six"
        words = re.split(r'[\s,]+', lower)
        digit_sequences = []
        current_seq = []
        current_start = 0
        pos = 0

        for word in words:
            word_clean = word.strip('.,!?')
            is_digit = False

            if word_clean in self.PHONETIC_DIGITS:
                if not current_seq:
                    current_start = lower.find(word, pos)
                current_seq.append(self.PHONETIC_DIGITS[word_clean])
                is_digit = True
            elif word_clean in self.NUMBER_WORDS:
                if not current_seq:
                    current_start = lower.find(word, pos)
                current_seq.append(self.NUMBER_WORDS[word_clean])
                is_digit = True

            if not is_digit and current_seq:
                # End of sequence
                combined = ''.join(current_seq)
                if len(combined) >= 3:
                    digit_sequences.append((combined, current_start, lower.find(word, pos)))
                current_seq = []

            pos = lower.find(word, pos) + len(word) if word in lower[pos:] else pos + len(word)

        # Don't forget trailing sequence
        if current_seq:
            combined = ''.join(current_seq)
            if len(combined) >= 3:
                digit_sequences.append((combined, current_start, len(lower)))

        # Check if any sequence looks like SSN or phone
        for digits, start, end in digit_sequences:
            # SSN pattern (9 digits)
            if len(digits) == 9 or (len(digits) >= 9 and len(digits) <= 11):
                matches.append(PIIMatch(
                    category=PIICategory.SSN,
                    severity=PIISeverity.CRITICAL,
                    content=text[start:end],
                    start=start,
                    end=end,
                    confidence=0.85,
                    reasoning="Phonetically encoded SSN detected",
                    redacted="[PHONETIC SSN]"
                ))
            # Phone pattern (10 digits)
            elif len(digits) == 10 or (len(digits) >= 10 and len(digits) <= 12):
                matches.append(PIIMatch(
                    category=PIICategory.PHONE,
                    severity=PIISeverity.HIGH,
                    content=text[start:end],
                    start=start,
                    end=end,
                    confidence=0.8,
                    reasoning="Phonetically encoded phone number detected",
                    redacted="[PHONETIC PHONE]"
                ))
            # Partial sequence (fragmentation risk)
            elif len(digits) >= 3:
                matches.append(PIIMatch(
                    category=PIICategory.FRAGMENTED,
                    severity=PIISeverity.MEDIUM,
                    content=text[start:end],
                    start=start,
                    end=end,
                    confidence=0.6,
                    reasoning=f"Phonetic digit sequence ({len(digits)} digits) - potential fragment",
                    redacted="[DIGIT SEQUENCE]"
                ))

        return matches


# =============================================================================
# Semantic Detection (Layer 2 - LLM-based)
# =============================================================================


SEMANTIC_PII_PROMPT = '''You are a PII (Personally Identifiable Information) detection system for a family law mediation application.

Analyze the following text for SEMANTIC PII - information that could identify individuals even without traditional patterns like SSN or phone numbers.

Categories to detect:
1. LOCATION_CONTEXTUAL: Descriptions that identify a specific location without an address
   - Example: "the blue house on Maple, third from the corner"
   - Example: "across from the elementary school with the red roof"

2. RELATIONSHIP: Names combined with relationships that could deanonymize
   - Example: "Little Joey" when context indicates only one minor child
   - Example: "my mother Susan who lives in El Paso"

3. SCHEDULE: Patterns revealing work, custody, or daily schedules
   - Example: "I always pick up at 3:15 on Wednesdays"
   - Example: "He works nights at the hospital"

4. MINOR_IDENTIFIER: Any information that could identify a child
   - Example: "My 7-year-old who goes to Lincoln Elementary"
   - Example: "the only redhead in his class"

5. EMPLOYER: Workplace identification
   - Example: "works at the only Toyota dealership in town"

6. MEDICAL: Health information
   - Example: "sees Dr. Martinez for his ADHD"

TEXT TO ANALYZE:
{text}

CONTEXT (previous messages summary):
{context}

Respond in JSON format:
{{
  "findings": [
    {{
      "category": "CATEGORY_NAME",
      "content": "exact text that contains PII",
      "severity": "critical|high|medium|low",
      "confidence": 0.0-1.0,
      "reasoning": "why this is identifiable"
    }}
  ],
  "overall_risk": 0.0-1.0,
  "reconstruction_concerns": "any patterns that could combine with other info"
}}

If no semantic PII found, return {{"findings": [], "overall_risk": 0.0, "reconstruction_concerns": null}}'''


class SemanticPIIDetector:
    """LLM-based semantic PII detection using Haiku for speed."""

    def __init__(
        self,
        llm_client: LLMClient,
        cache_ttl_seconds: int = 3600,
        max_context_chars: int = 2000
    ):
        self.llm = llm_client
        self.cache_ttl = cache_ttl_seconds
        self.max_context = max_context_chars

        # Content-addressable cache: hash(text) -> (PIIAnalysis, timestamp)
        self._cache: dict[str, tuple[list[PIIMatch], float]] = {}

    def _content_hash(self, text: str, context: str) -> str:
        """Generate cache key from content."""
        combined = f"{text}|||{context}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    def _check_cache(self, text: str, context: str) -> list[PIIMatch] | None:
        """Check if we have cached results."""
        key = self._content_hash(text, context)
        if key in self._cache:
            matches, timestamp = self._cache[key]
            if time.time() - timestamp < self.cache_ttl:
                return matches
            else:
                del self._cache[key]
        return None

    def _update_cache(self, text: str, context: str, matches: list[PIIMatch]) -> None:
        """Update cache with new results."""
        key = self._content_hash(text, context)
        self._cache[key] = (matches, time.time())

        # Prune old entries (simple LRU-ish)
        if len(self._cache) > 1000:
            oldest_key = min(self._cache, key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]

    async def detect(
        self,
        text: str,
        context_summary: str = ""
    ) -> tuple[list[PIIMatch], float, str | None]:
        """
        Run semantic PII detection.

        Returns:
            (matches, overall_risk, reconstruction_concerns)
        """
        # Check cache
        cached = self._check_cache(text, context_summary)
        if cached is not None:
            return cached, 0.0, None  # Can't recover risk/concerns from cache

        # Truncate context if needed
        context = context_summary[:self.max_context] if context_summary else "No prior context"

        prompt = SEMANTIC_PII_PROMPT.format(text=text, context=context)

        try:
            response = await self.llm.complete(prompt)
            result = json.loads(response)
        except (json.JSONDecodeError, Exception) as e:
            # On LLM failure, return empty but flag as uncertain
            return [], 0.5, f"LLM analysis failed: {e}"

        matches = []
        for finding in result.get("findings", []):
            category_name = finding.get("category", "").upper()
            try:
                category = PIICategory[category_name]
            except KeyError:
                category = PIICategory.RELATIONSHIP  # Default fallback

            severity_name = finding.get("severity", "medium").upper()
            try:
                severity = PIISeverity[severity_name]
            except KeyError:
                severity = PIISeverity.MEDIUM

            content = finding.get("content", "")
            start = text.find(content) if content else 0
            end = start + len(content) if content else 0

            matches.append(PIIMatch(
                category=category,
                severity=severity,
                content=content,
                start=start,
                end=end,
                confidence=finding.get("confidence", 0.7),
                reasoning=finding.get("reasoning", "Semantic analysis"),
                redacted=f"[{category.value.upper()}]"
            ))

        self._update_cache(text, context_summary, matches)

        return (
            matches,
            result.get("overall_risk", 0.0),
            result.get("reconstruction_concerns")
        )


# =============================================================================
# Document/Binary Content Detection
# =============================================================================


class DocumentPIIScanner:
    """
    Scans document content (OCR'd PDFs, screenshots) for PII.

    Uses a combination of:
    - Text extraction (delegated to caller)
    - Regex scanning of extracted text
    - Semantic analysis of extracted text
    - Image metadata inspection
    """

    # Metadata fields that may contain PII
    RISKY_METADATA = {
        'author', 'creator', 'producer', 'company', 'manager',
        'title', 'subject', 'keywords', 'comments',
        'gps', 'geolocation', 'location',
    }

    def __init__(
        self,
        regex_detector: RegexPIIDetector,
        semantic_detector: SemanticPIIDetector
    ):
        self.regex = regex_detector
        self.semantic = semantic_detector

    def scan_metadata(self, metadata: dict[str, Any]) -> list[PIIMatch]:
        """Scan document metadata for PII."""
        matches = []

        for key, value in metadata.items():
            if not isinstance(value, str):
                continue

            key_lower = key.lower()

            # Check if field name itself is risky
            if any(risky in key_lower for risky in self.RISKY_METADATA):
                matches.append(PIIMatch(
                    category=PIICategory.RELATIONSHIP,
                    severity=PIISeverity.MEDIUM,
                    content=f"{key}: {value}",
                    start=0,
                    end=0,
                    confidence=0.7,
                    reasoning=f"Metadata field '{key}' may contain identifying information",
                    redacted=f"[METADATA:{key.upper()}]"
                ))

            # Run regex on value
            regex_matches = self.regex.detect(value)
            for m in regex_matches:
                m.reasoning = f"Found in metadata field '{key}': {m.reasoning}"
            matches.extend(regex_matches)

        return matches

    async def scan_extracted_text(
        self,
        text: str,
        context_summary: str = "",
        source: str = "document"
    ) -> list[PIIMatch]:
        """Scan OCR'd or extracted text for PII."""
        matches = []

        # Layer 1: Regex
        regex_matches = self.regex.detect(text)
        for m in regex_matches:
            m.reasoning = f"[{source}] {m.reasoning}"
        matches.extend(regex_matches)

        # Layer 2: Semantic (only if text is substantial)
        if len(text) > 50:
            semantic_matches, _, _ = await self.semantic.detect(text, context_summary)
            for m in semantic_matches:
                m.reasoning = f"[{source}] {m.reasoning}"
            matches.extend(semantic_matches)

        return matches


# =============================================================================
# Unified PII Detector
# =============================================================================


class PIIDetector:
    """
    Unified PII detection combining regex, semantic, and fragmentation analysis.

    Usage:
        detector = PIIDetector(llm_client)
        result = await detector.analyze(
            message_id="msg-123",
            text="My ex lives at the blue house...",
            session_id="session-456"
        )
        if not result.safe:
            # Handle PII detection
    """

    # Severity thresholds for blocking
    BLOCK_SEVERITIES = {PIISeverity.CRITICAL}
    WARN_SEVERITIES = {PIISeverity.HIGH}

    def __init__(
        self,
        llm_client: LLMClient,
        cache_ttl_seconds: int = 3600,
        fragmentation_window_hours: int = 4,
        enable_semantic: bool = True
    ):
        self.regex_detector = RegexPIIDetector()
        self.semantic_detector = SemanticPIIDetector(
            llm_client,
            cache_ttl_seconds
        ) if enable_semantic else None

        self.fragmentation_window = fragmentation_window_hours

        # Session state for fragmentation tracking
        self._sessions: dict[str, FragmentedPIIState] = {}

    def _get_session(self, session_id: str) -> FragmentedPIIState:
        """Get or create session state."""
        if session_id not in self._sessions:
            self._sessions[session_id] = FragmentedPIIState(session_id=session_id)
        return self._sessions[session_id]

    def _build_context_summary(self, session: FragmentedPIIState) -> str:
        """Build context summary from session state for semantic analysis."""
        parts = []

        if session.mentioned_names:
            parts.append(f"Names mentioned: {', '.join(list(session.mentioned_names)[:10])}")

        if session.mentioned_locations:
            parts.append(f"Locations discussed: {', '.join(session.mentioned_locations[-5:])}")

        fragment_counts = {
            cat.value: len(frags)
            for cat, frags in session.fragments.items()
            if frags
        }
        if fragment_counts:
            parts.append(f"PII fragments detected: {fragment_counts}")

        return " | ".join(parts) if parts else ""

    async def analyze(
        self,
        message_id: str,
        text: str,
        session_id: str | None = None,
        document_metadata: dict[str, Any] | None = None,
        timestamps: list[datetime] | None = None
    ) -> PIIAnalysis:
        """
        Analyze text for PII.

        Args:
            message_id: Unique identifier for this message
            text: The text content to analyze
            session_id: Session ID for fragmentation tracking (optional)
            document_metadata: Metadata from documents (optional)
            timestamps: Timestamps to check for schedule patterns (optional)

        Returns:
            PIIAnalysis with all detected PII
        """
        start_time = time.time()
        matches: list[PIIMatch] = []

        # Get/create session state
        session = self._get_session(session_id) if session_id else None

        # Layer 1: Regex detection (fast)
        regex_matches = self.regex_detector.detect(text)
        matches.extend(regex_matches)

        # Layer 2: Semantic detection (LLM-based)
        semantic_risk = 0.0
        if self.semantic_detector and len(text) > 20:
            context = self._build_context_summary(session) if session else ""
            semantic_matches, semantic_risk, concerns = await self.semantic_detector.detect(
                text, context
            )
            matches.extend(semantic_matches)

            # Log reconstruction concerns
            if concerns and session:
                session.fragments[PIICategory.FRAGMENTED].append(
                    (concerns, datetime.now(), message_id)
                )

        # Layer 3: Document metadata scanning
        if document_metadata:
            doc_scanner = DocumentPIIScanner(self.regex_detector, self.semantic_detector)
            meta_matches = doc_scanner.scan_metadata(document_metadata)
            matches.extend(meta_matches)

        # Layer 4: Timestamp/schedule pattern detection
        if timestamps and len(timestamps) >= 3:
            schedule_matches = self._detect_schedule_patterns(timestamps)
            matches.extend(schedule_matches)

        # Layer 5: Fragmentation check (cross-message)
        if session:
            # Update session with new fragments
            for match in matches:
                if match.category in {PIICategory.SSN, PIICategory.PHONE}:
                    session.add_fragment(
                        match.category,
                        match.content,
                        datetime.now(),
                        message_id
                    )

            # Extract names for future context
            name_pattern = re.compile(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b')
            for name_match in name_pattern.finditer(text):
                session.mentioned_names.add(name_match.group())

            # Check for reconstructable PII
            reconstruction_matches = session.check_reconstruction(
                self.fragmentation_window
            )
            matches.extend(reconstruction_matches)

            # Prune old fragments
            session.prune_old(hours=8)

        # Determine if safe
        blocking_matches = [m for m in matches if m.severity in self.BLOCK_SEVERITIES]
        warning_matches = [m for m in matches if m.severity in self.WARN_SEVERITIES]

        safe = len(blocking_matches) == 0

        # Generate redacted text
        redacted_text = self._redact_text(text, matches) if matches else None

        # Calculate risk score
        risk_score = self._calculate_risk_score(matches, semantic_risk)

        latency_ms = (time.time() - start_time) * 1000

        return PIIAnalysis(
            message_id=message_id,
            timestamp=datetime.now(),
            matches=matches,
            safe=safe,
            redacted_text=redacted_text,
            risk_score=risk_score,
            latency_ms=latency_ms
        )

    def _detect_schedule_patterns(self, timestamps: list[datetime]) -> list[PIIMatch]:
        """Detect schedule patterns from timestamps."""
        matches = []

        # Group by day of week
        day_times: dict[int, list[int]] = defaultdict(list)  # weekday -> [hours]
        for ts in timestamps:
            day_times[ts.weekday()].append(ts.hour)

        # Look for consistent patterns (same time on same day)
        for weekday, hours in day_times.items():
            if len(hours) >= 2:
                # Check for consistent timing
                hour_counts = defaultdict(int)
                for h in hours:
                    hour_counts[h] += 1

                for hour, count in hour_counts.items():
                    if count >= 2:
                        day_name = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][weekday]
                        matches.append(PIIMatch(
                            category=PIICategory.SCHEDULE,
                            severity=PIISeverity.MEDIUM,
                            content=f"Pattern: {day_name} at {hour}:00",
                            start=0,
                            end=0,
                            confidence=0.6,
                            reasoning=f"Detected {count} messages on {day_name}s around {hour}:00 - reveals schedule pattern",
                            redacted="[SCHEDULE PATTERN]"
                        ))

        return matches

    def _redact_text(self, text: str, matches: list[PIIMatch]) -> str:
        """Generate redacted version of text."""
        if not matches:
            return text

        # Sort by position (reverse to maintain indices)
        sorted_matches = sorted(
            [m for m in matches if m.start > 0 or m.end > 0],
            key=lambda m: m.start,
            reverse=True
        )

        result = text
        for match in sorted_matches:
            if match.start < match.end:
                result = result[:match.start] + match.redacted + result[match.end:]

        return result

    def _calculate_risk_score(
        self,
        matches: list[PIIMatch],
        semantic_risk: float
    ) -> float:
        """Calculate overall risk score 0.0 - 1.0."""
        if not matches:
            return max(0.0, semantic_risk * 0.5)

        # Weight by severity
        severity_weights = {
            PIISeverity.CRITICAL: 1.0,
            PIISeverity.HIGH: 0.7,
            PIISeverity.MEDIUM: 0.4,
            PIISeverity.LOW: 0.2,
        }

        weighted_sum = sum(
            severity_weights[m.severity] * m.confidence
            for m in matches
        )

        # Normalize (cap at 1.0)
        match_risk = min(1.0, weighted_sum / 3)

        # Combine with semantic risk
        return min(1.0, match_risk * 0.7 + semantic_risk * 0.3)

    def clear_session(self, session_id: str) -> None:
        """Clear session state."""
        if session_id in self._sessions:
            del self._sessions[session_id]

    def get_session_risk_summary(self, session_id: str) -> dict[str, Any]:
        """Get risk summary for a session."""
        session = self._sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}

        return {
            "session_id": session_id,
            "fragment_counts": {
                cat.value: len(frags)
                for cat, frags in session.fragments.items()
                if frags
            },
            "names_mentioned": len(session.mentioned_names),
            "ssn_fragments": len(session.potential_ssn_digits),
            "phone_fragments": len(session.potential_phone_digits),
            "reconstruction_possible": bool(session.check_reconstruction())
        }


# =============================================================================
# Secure Router Integration
# =============================================================================


class PIIGuard:
    """
    Guards content flow to external models.

    Usage:
        guard = PIIGuard(detector)

        # Check before sending to external model
        if await guard.is_safe_for_external(content, session_id):
            send_to_groq(content)
        else:
            # Keep in Claude-only
            send_to_claude(content)
    """

    def __init__(
        self,
        detector: PIIDetector,
        block_on_warning: bool = False
    ):
        self.detector = detector
        self.block_on_warning = block_on_warning

    async def is_safe_for_external(
        self,
        content: str,
        session_id: str | None = None
    ) -> bool:
        """Check if content is safe to send to external models."""
        import uuid

        result = await self.detector.analyze(
            message_id=str(uuid.uuid4()),
            text=content,
            session_id=session_id
        )

        if not result.safe:
            return False

        if self.block_on_warning:
            has_warnings = any(
                m.severity == PIISeverity.HIGH
                for m in result.matches
            )
            if has_warnings:
                return False

        return True

    async def filter_for_external(
        self,
        content: str,
        session_id: str | None = None
    ) -> tuple[str, PIIAnalysis]:
        """
        Filter content for external model use.

        Returns:
            (filtered_content, analysis)
        """
        import uuid

        result = await self.detector.analyze(
            message_id=str(uuid.uuid4()),
            text=content,
            session_id=session_id
        )

        if result.redacted_text:
            return result.redacted_text, result
        return content, result


class SecureModelRouter:
    """
    Routes messages to appropriate models based on PII content.

    Enforces Karen's recommendation:
    - Legal strategy & PII -> Claude only
    - Public case law, general research -> External OK
    """

    def __init__(
        self,
        pii_guard: PIIGuard,
        claude_client: Any,  # Your Claude client
        external_client: Any | None = None  # Groq/Ollama client
    ):
        self.guard = pii_guard
        self.claude = claude_client
        self.external = external_client

    async def route(
        self,
        content: str,
        session_id: str | None = None,
        prefer_external: bool = False
    ) -> tuple[str, str]:
        """
        Route content to appropriate model.

        Returns:
            (model_used, response)
        """
        # Always check PII first
        safe = await self.guard.is_safe_for_external(content, session_id)

        if safe and prefer_external and self.external:
            # Safe for external
            try:
                response = await self.external.complete(content)
                return "external", response
            except Exception:
                # Fallback to Claude
                pass

        # Use Claude (default for PII content)
        response = await self.claude.complete(content)
        return "claude", response
