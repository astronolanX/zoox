# Reef Statusline with Spark Grades

Using spark's square ASCII grading system for reef vitality components.

---

## Spark Grade System (Reused)

```bash
██  # ≥80 (high confidence)
▓▓  # ≥60 (medium-high)
░░  # ≥40 (medium-low)
··  # <40 (low)
```

---

## Reef Vitality with Spark Grades

### Current State (40/100 declining)

```
🟠 Vitality: 40/100
├─ Activity  ██ 25/25  ✓
├─ Quality   ·· 0/25   ⚠
├─ Resonance ·· 0/25   ⚠
└─ Health    ░░ 15/25  ⚠
```

### Thriving State (85/100)

```
🟢 Vitality: 85/100
├─ Activity  ██ 25/25  ✓
├─ Quality   ██ 22/25  ✓
├─ Resonance ██ 20/25  ✓
└─ Health    ▓▓ 18/25  ✓
```

### Dying State (12/100)

```
🔴 Vitality: 12/100
├─ Activity  ·· 2/25   ⚠
├─ Quality   ·· 0/25   ⚠
├─ Resonance ·· 0/25   ⚠
└─ Health    ░░ 10/25  ⚠
```

---

## Component Thresholds

Each component scored 0-25, mapped to spark grades:

```python
def score_to_grade(score: int, max_score: int = 25) -> str:
    """Convert 0-25 score to spark grade."""
    pct = (score / max_score) * 100
    if pct >= 80:
        return "██"
    elif pct >= 60:
        return "▓▓"
    elif pct >= 40:
        return "░░"
    else:
        return "··"
```

**Mapping:**
- Activity 25/25 = 100% → `██`
- Quality 0/25 = 0% → `··`
- Resonance 0/25 = 0% → `··`
- Health 15/25 = 60% → `▓▓`

---

## Compact Format with Grades

```bash
# Instead of:
~/reef 🟠 40 [15p 0t 83%] $

# Show component grades:
~/reef 🟠 40 [██··░░▓▓] $
           ^  ^ ^ ^ ^
           │  │ │ └─ health
           │  │ └─ resonance
           │  └─ quality
           └─ activity
```

**Examples:**
```
~/reef 🟢 85 [████████] $  # All components strong
~/reef 🟠 40 [██····▓▓] $  # Activity good, quality/resonance weak
~/reef 🔴 12 [········] $  # Everything critical
```

---

## Extended Format (All Metrics)

```bash
# Full breakdown:
~/reef 🟠 40 [a:██ q:·· r:·· h:▓▓] $

# With counts:
~/reef 🟠 40 [15p 0t] [██··░░▓▓] $
```

---

## Shell Functions

### zsh Integration

```bash
# ~/.zshrc
function reef_vitality_grade() {
  local status_file="/tmp/reef-$(basename $PWD).status"

  if [[ ! -f "$status_file" ]]; then
    return
  fi

  # Parse vitality components
  local activity=$(jq -r '.vitality.components.activity' "$status_file" 2>/dev/null)
  local quality=$(jq -r '.vitality.components.quality' "$status_file" 2>/dev/null)
  local resonance=$(jq -r '.vitality.components.resonance' "$status_file" 2>/dev/null)
  local health=$(jq -r '.vitality.components.health' "$status_file" 2>/dev/null)

  # Convert to grades
  local a=$(score_to_grade $activity)
  local q=$(score_to_grade $quality)
  local r=$(score_to_grade $resonance)
  local h=$(score_to_grade $health)

  echo "[$a$q$r$h]"
}

function score_to_grade() {
  local score=$1
  local pct=$((score * 100 / 25))

  if [[ $pct -ge 80 ]]; then
    echo "██"
  elif [[ $pct -ge 60 ]]; then
    echo "▓▓"
  elif [[ $pct -ge 40 ]]; then
    echo "░░"
  else
    echo "··"
  fi
}

# Add to prompt
PROMPT='%~ $(reef_vitality_grade) $ '
```

---

## Comparison Table

| State | Overall | Activity | Quality | Resonance | Health | Grade Display |
|-------|---------|----------|---------|-----------|--------|---------------|
| **Thriving** | 🟢 85 | 25/25 | 22/25 | 20/25 | 18/25 | `[████▓▓]` |
| **Stable** | 🟡 62 | 20/25 | 15/25 | 15/25 | 12/25 | `[██▓▓▓▓░░]` |
| **Declining** | 🟠 40 | 25/25 | 0/25 | 0/25 | 15/25 | `[██····▓▓]` |
| **Dying** | 🔴 12 | 2/25 | 0/25 | 0/25 | 10/25 | `[········]` |

---

## Visual Benefits

1. **Consistency**: Same grading system as spark plugin
2. **Compact**: 8 chars vs 100+ char bars
3. **Scannable**: Instant visual pattern recognition
4. **Familiar**: Users already know spark grades

---

## Implementation

```python
# In blob.py write_status()
def _component_to_grade(score: int, max_score: int = 25) -> str:
    """Convert component score to spark grade."""
    pct = (score / max_score) * 100
    if pct >= 80:
        return "██"
    elif pct >= 60:
        return "▓▓"
    elif pct >= 40:
        return "░░"
    else:
        return "··"

# Add to status dict
vitality_data["grades"] = {
    "activity": _component_to_grade(activity_score),
    "quality": _component_to_grade(quality_score),
    "resonance": _component_to_grade(resonance_score),
    "health": _component_to_grade(health_score),
    "compact": f"{a_grade}{q_grade}{r_grade}{h_grade}"
}
```

---

## Recommended Formats

### 1. Minimal with Grades
```
~/reef 🟠 40 [██····▓▓] $
```

### 2. Labeled Grades
```
~/reef 🟠 40 [a:██ q:·· r:·· h:▓▓] $
```

### 3. Mixed (counts + grades)
```
~/reef 🟠 40 [15p 0t] [██····▓▓] $
```

### 4. Component Breakdown
```
🟠 40/100
├─ Activity  ██ 25
├─ Quality   ·· 0
├─ Resonance ·· 0
└─ Health    ▓▓ 15
```

---

## Pattern Recognition

Users can quickly spot patterns:

- `[████████]` = All systems go (thriving)
- `[██▓▓▓▓▓▓]` = Solid, minor improvements needed (stable)
- `[██····░░]` = Good activity but weak content (declining)
- `[········]` = Critical across the board (dying)

The visual shape tells the story at a glance.
