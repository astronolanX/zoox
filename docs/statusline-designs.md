# Reef MCP Statusline Designs

Visual mockups for how reef vitality appears in shell prompts, IDEs, and status bars.

---

## 1. Minimal (Icon + Score)
**Target:** tmux, zsh prompt, minimal overhead
```
🟢 85  # Thriving
🟡 62  # Stable
🟠 40  # Declining
🔴 12  # Dying
```

**Prompt integration:**
```bash
~/project (main) 🟢 85 $
~/project (main) 🟠 40 $
```

---

## 2. Compact (Icon + Metrics)
**Target:** Shell prompt with key metrics
```
🟢 85 [15p 4t 83%]    # 15 polips, 4 trenches, 83% token savings
🟡 62 [8p 0t 75%]     # 8 polips, no trenches, 75% savings
🟠 40 [15p 0t 83%]    # Declining despite good size
🔴 12 [3p 0t 20%]     # Dying, minimal content
```

**Prompt:**
```bash
~/reef (main) 🟠 40 [15p 0t 83%] $
```

---

## 3. Component Bars (Visual Breakdown)
**Target:** Terminal status bar, rich clients
```
🟢 Vitality: 85/100
├─ Activity  ████████████████████████░ 25/25
├─ Quality   ████████████████████░░░░░ 20/25
├─ Resonance █████████████████░░░░░░░░ 17/25
└─ Health    ███████████████████████░░ 23/25

🟠 Vitality: 40/100
├─ Activity  █████████████████████████ 25/25  ✓
├─ Quality   ░░░░░░░░░░░░░░░░░░░░░░░░░  0/25  ⚠
├─ Resonance ░░░░░░░░░░░░░░░░░░░░░░░░░  0/25  ⚠
└─ Health    ███████████████░░░░░░░░░░ 15/25  ⚠
```

**Tooltip/hover:**
```
Reef Health: 40/100 (declining)
→ Enrich polips with facts and decisions
```

---

## 4. Alert-First (Problems Front)
**Target:** Notification systems, alerts
```
⚠ Reef declining (40) - No polip links
✓ Reef stable (62) - 2d since activity
🔴 Reef dying (12) - Stale polips: 8
🟢 Reef thriving (85)
```

**With action:**
```
⚠ Declining (40) → Add facts to polips
🔴 Dying (12) → Run: reef sink
🟡 Stable (62) → Create new content
```

**Prompt:**
```bash
~/reef ⚠ declining → add facts $
```

---

## 5. Trend-Based (Change Over Time)
**Target:** Dashboard, analytics view
```
🟢 85 ↑+12  (thriving, up from 73)
🟡 62 →     (stable, unchanged)
🟠 40 ↓-8   (declining, down from 48)
🔴 12 ↓-15  (dying, down from 27)
```

**With timestamp:**
```
🟠 40 ↓-8 (2h ago)
🟢 85 ↑+12 (just now)
```

---

## 6. Activity-Focused (Recent Actions)
**Target:** IDE sidebar, dashboard
```
🟢 85  Last: spawned thread 5m ago
🟡 62  Last: updated polip 2d ago
🟠 40  Last: indexed 3h ago
🔴 12  Last: activity 14d ago
```

**With next action:**
```
🟠 40  Last: 3h → Link related polips
🔴 12  Last: 14d → Add new content urgently
```

---

## 7. Rich Context (Multi-Line)
**Target:** Terminal splash, `reef status` command
```
┌─ Reef Health ──────────────────┐
│ 🟢 Thriving (85/100)           │
│                                │
│ 15 polips • 4 trenches active │
│ 83% token savings             │
│ Last activity: 5m ago         │
│                                │
│ ✓ Quality content             │
│ ✓ Good linking patterns       │
│ ✓ Recent updates              │
└────────────────────────────────┘
```

**Declining state:**
```
┌─ Reef Health ──────────────────┐
│ 🟠 Declining (40/100)          │
│                                │
│ 15 polips • 0 trenches        │
│ 83% token savings             │
│ Last activity: today          │
│                                │
│ ⚠ No facts or decisions       │
│ ⚠ Polips not linked           │
│ ⚠ Isolated content            │
│                                │
│ 💡 Add facts to polips         │
└────────────────────────────────┘
```

---

## 8. Gamified (Progress Bar + Level)
**Target:** User engagement, gamification
```
🟢 Lv.8 ████████████████████░░░░░ 85/100 (Thriving Reef)
🟡 Lv.6 ████████████░░░░░░░░░░░░░ 62/100 (Stable Ecosystem)
🟠 Lv.4 ████████░░░░░░░░░░░░░░░░░ 40/100 (Needs Nutrients)
🔴 Lv.1 ███░░░░░░░░░░░░░░░░░░░░░░ 12/100 (Critical)
```

**With achievements:**
```
🟢 Lv.8 85/100 🏆 First Thriving Reef
🟠 Lv.4 40/100 ⭐ 10 Polips Created
```

---

## 9. Developer-Focused (Metrics + Commands)
**Target:** Terminal power users
```
reef: 40/100 🟠 | polips:15 trenches:0 tokens:83% | ⚠ quality:0/25
reef: 85/100 🟢 | polips:23 trenches:2 tokens:91% | ✓ all systems go

# With suggested command
reef: 40/100 🟠 | ⚠ quality:0/25 → reef sprout thread "..."
reef: 12/100 🔴 | ⚠ stale:8 → reef sink --days 30
```

**Prompt integration:**
```bash
~/reef (main) | 🟠 40 quality:0/25 $
```

---

## 10. Contextual (Adapts to Situation)
**Target:** Smart notifications, context-aware UI

**During active development:**
```
🟢 85 | 2 trenches running | Last commit: 5m
```

**After long break:**
```
🟡 62 | Last activity: 2d ago | Welcome back!
```

**Multiple people working:**
```
🟢 85 | 3 contributors active | 5 new polips today
```

**Urgent attention needed:**
```
🔴 12 | 8 stale polips | 🚨 Reef needs maintenance
```

---

## Implementation Notes

### MCP Integration Points

1. **Status Provider** - MCP tool returns current vitality
```typescript
// MCP call
const status = await mcp.call("reef_get_status")
// Returns: { score: 40, status: "declining", icon: "🟠", ... }
```

2. **Stream Updates** - Real-time statusline updates
```typescript
mcp.subscribe("reef_vitality_changed", (vitality) => {
  updateStatusline(vitality)
})
```

3. **Action Prompts** - Clickable recommendations
```typescript
if (vitality.status === "declining") {
  showNotification(vitality.recommended_action, {
    action: "Open reef health",
    command: "reef health"
  })
}
```

### Configuration

Users choose their preferred format:
```json
{
  "reef.statusline.format": "compact",  // minimal|compact|rich|alert
  "reef.statusline.show_in_prompt": true,
  "reef.statusline.show_trends": true,
  "reef.statusline.notify_threshold": "declining"
}
```

---

## Recommended Defaults

- **Shell prompt**: Format #2 (Compact)
- **tmux status**: Format #1 (Minimal)
- **IDE sidebar**: Format #7 (Rich Context)
- **Notifications**: Format #4 (Alert-First)
- **Dashboard**: Format #5 (Trend-Based)
