@current v1 2026-01-16
.current format specification
AI-native syntax for active work streams

---DESIGN PRINCIPLES---

>tokenDensity
 Every character carries semantic weight
 No closing tags, no quotes around simple values
 Whitespace is structure, not decoration

>parseSpeed
 Line-oriented: one semantic unit per line
 Prefix sigils: instant type recognition
 Position encodes meaning (no key:value pairs needed)

>attentionOptimized
 Front-load important tokens (summaries first)
 Group related facts for locality of reference
 Sigils create attention anchors transformers see instantly

---SIGIL VOCABULARY---

@ header/metadata (what this is)
# summary (the single sentence truth)
> section marker (attention anchor)
! active/urgent (high priority signal)
? open question (unresolved)
+ fact/truth (known)
- anti-pattern (known bad)
= decision (resolved)
~ context (background)
* step/action (todo)
^ reference (link to other polip)
& checkpoint (state marker)
| stream (parallel track)

---SYNTAX RULES---

1. First line is always @current followed by stream-id and date
2. Second line is bare summary (no sigil needed - position encodes it)
3. Sections start with > and lowercase name
4. Indentation: single space for continuation
5. Multi-line content: indent by 1 space from sigil
6. References use ^polip-id inline or standalone
7. Checkpoints mark state: &active &paused &blocked &done

---MINIMAL EXAMPLE---

@current vitality-impl 2026-01-16
Implementing reef vitality scoring system
&active

>facts
+Living systems respond to signals
+Content flow indicates health
+Voice consistency emerges from aligned inference

>decisions
=Vitality measured by content quality not volume
=Growth equals inference resonance not polip count

>open
?How to detect voice drift algorithmically
?What threshold triggers auto-pruning

>next
*Define toxic content signals
*Implement vitality scoring
 voice consistency
 inference alignment
 content freshness
*Build reef response mechanisms

>refs
^threads-reef-native-infrastructure
^constraints-project-rules

---PARSER BEHAVIOR---

Line starts with sigil: extract sigil, rest is content
Line starts with space: continuation of previous
Line starts with >: new section, name follows
Empty line: section boundary
@: stream metadata
&: state transition

---WHY NOT XML/JSON/YAML---

XML: 50%+ tokens wasted on closing tags
JSON: quotes around every string, commas, braces
YAML: indentation ambiguity, verbose keys
Markdown: human-readable != AI-parseable

.current achieves:
- 3x token density vs XML
- Instant sigil recognition (no lookahead needed)
- Line-oriented streaming parse
- Zero ambiguity in structure

---EXTENSION---

Custom sigils via >vocab section:
>vocab
% probability/uncertainty
/ alternative path
& checkpoint (override default)

Parser inherits base vocabulary, extends with custom.

---VALIDATION---

Valid .current:
- Starts with @current
- Has summary on line 2
- Has at least one &state marker
- All ^refs resolve to existing polips

Warning only:
- Empty sections
- No >next section (stream may be complete)
- Stale date (>7 days without &active)
