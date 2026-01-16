# Reef MCP Statusline Protocol

How reef vitality integrates with MCP servers for real-time statusline updates.

---

## MCP Tools

### 1. `reef_get_status` - Get Current Vitality

**Request:**
```json
{
  "name": "reef_get_status",
  "arguments": {
    "format": "compact"  // optional: minimal|compact|full
  }
}
```

**Response:**
```json
{
  "score": 40,
  "status": "declining",
  "icon": "🟠",
  "last_activity": "2026-01-16",
  "days_since_activity": 0,
  "recommended_action": "Enrich polips with facts and decisions",
  "components": {
    "activity": 25,
    "quality": 0,
    "resonance": 0,
    "health": 15
  },
  "metrics": {
    "polip_count": 15,
    "trench_count": 0,
    "token_savings_pct": 83,
    "avg_facts": 0.0,
    "avg_links": 0.0,
    "stale_count": 0,
    "isolated_count": 15
  }
}
```

### 2. `reef_format_statusline` - Format for Display

**Request:**
```json
{
  "name": "reef_format_statusline",
  "arguments": {
    "format": "compact",
    "include_metrics": true,
    "show_action": false
  }
}
```

**Response (compact):**
```json
{
  "text": "🟠 40 [15p 0t 83%]",
  "full_text": "Reef declining (40/100) - 15 polips, 0 trenches, 83% token savings",
  "color": "#ff9500",  // CSS color for UI
  "urgency": "warning"  // none|info|warning|critical
}
```

**Response (minimal):**
```json
{
  "text": "🟠 40",
  "full_text": "Reef declining (40/100)",
  "color": "#ff9500",
  "urgency": "warning"
}
```

**Response (alert):**
```json
{
  "text": "⚠ Declining (40) → Add facts",
  "full_text": "Reef declining (40/100) - Enrich polips with facts and decisions",
  "color": "#ff9500",
  "urgency": "warning",
  "action": {
    "label": "Add facts to polips",
    "command": "Open editor",
    "hint": "Edit .claude/threads/*.xml"
  }
}
```

### 3. `reef_subscribe_vitality` - Real-time Updates

**Request:**
```json
{
  "name": "reef_subscribe_vitality",
  "arguments": {
    "threshold": "declining"  // notify when status <= declining
  }
}
```

**Stream Events:**
```json
// On vitality change
{
  "event": "vitality_changed",
  "data": {
    "score": 45,
    "status": "declining",
    "previous_score": 40,
    "delta": 5,
    "trend": "improving"
  }
}

// On status transition
{
  "event": "status_transition",
  "data": {
    "from": "declining",
    "to": "stable",
    "score": 52,
    "trigger": "Added 3 facts to polips"
  }
}

// On alert
{
  "event": "health_alert",
  "data": {
    "severity": "warning",
    "message": "Reef declining - No polip links",
    "action": "Link related polips using [[polip-name]]"
  }
}
```

---

## Client Integration Examples

### Shell Prompt (zsh)

```bash
# ~/.zshrc
function reef_prompt() {
  local status=$(reef shell --hint --format compact 2>/dev/null)
  if [[ -n "$status" ]]; then
    echo " $status"
  fi
}

PROMPT='%~ $(reef_prompt) $ '
```

**Result:**
```
~/reef 🟠 40 [15p 0t 83%] $
```

### tmux Status Bar

```bash
# ~/.tmux.conf
set -g status-right '#(reef shell --hint --format minimal) | %H:%M'
```

**Result:**
```
[...] 🟠 40 | 14:23
```

### VS Code Extension

```typescript
// extension.ts
import { MCP } from '@modelcontextprotocol/sdk'

const mcp = new MCP('reef')

// Update statusline every 30s
setInterval(async () => {
  const status = await mcp.call('reef_get_status', { format: 'compact' })

  vscode.window.setStatusBarMessage(
    `$(reef-icon) ${status.text}`,
    {
      tooltip: status.full_text,
      command: status.score < 50 ? 'reef.showHealth' : undefined
    }
  )
}, 30000)

// Real-time updates
mcp.subscribe('vitality_changed', (event) => {
  if (event.data.trend === 'declining') {
    vscode.window.showWarningMessage(
      `Reef health declining: ${event.data.score}/100`,
      'View Health', 'Dismiss'
    ).then(selection => {
      if (selection === 'View Health') {
        vscode.commands.executeCommand('reef.showHealth')
      }
    })
  }
})
```

### Raycast Extension

```typescript
// reef-status.tsx
import { Detail, showToast, Toast } from "@raycast/api"
import { MCP } from "@modelcontextprotocol/sdk"

export default function ReefStatus() {
  const [status, setStatus] = useState(null)

  useEffect(() => {
    const mcp = new MCP('reef')
    mcp.call('reef_get_status', { format: 'full' })
      .then(setStatus)
  }, [])

  if (!status) return <Detail isLoading />

  const markdown = `
# ${status.icon} Reef ${status.status} (${status.score}/100)

## Components
- Activity: ${status.components.activity}/25
- Quality: ${status.components.quality}/25
- Resonance: ${status.components.resonance}/25
- Health: ${status.components.health}/25

## Metrics
- Polips: ${status.metrics.polip_count}
- Trenches: ${status.metrics.trench_count}
- Token savings: ${status.metrics.token_savings_pct}%

${status.recommended_action && `💡 **${status.recommended_action}**`}
`

  return <Detail markdown={markdown} />
}
```

### Claude Desktop MCP Integration

```json
// claude_desktop_config.json
{
  "mcpServers": {
    "reef": {
      "command": "uv",
      "args": ["run", "reef", "mcp"],
      "env": {
        "REEF_STATUSLINE_FORMAT": "compact",
        "REEF_NOTIFY_THRESHOLD": "declining"
      }
    }
  }
}
```

**Tools available in Claude:**
```
Available tools:
- reef_get_status: Get current reef vitality score
- reef_format_statusline: Format vitality for display
- reef_get_recommendations: Get actionable health advice
- reef_surface_polips: Surface relevant polips with vitality awareness
```

---

## Format Specifications

### Compact Format
```
{icon} {score} [{polips}p {trenches}t {savings}%]

Examples:
🟢 85 [15p 4t 83%]
🟠 40 [15p 0t 83%]
🔴 12 [3p 0t 20%]
```

### Minimal Format
```
{icon} {score}

Examples:
🟢 85
🟠 40
🔴 12
```

### Alert Format
```
{severity} {status} ({score}) → {action}

Examples:
⚠ Declining (40) → Add facts
🔴 Dying (12) → Run: reef sink
🟢 Thriving (85)
```

### Rich Format
```
{icon} Vitality: {score}/100
├─ Activity  {bar} {value}/25  {status}
├─ Quality   {bar} {value}/25  {status}
├─ Resonance {bar} {value}/25  {status}
└─ Health    {bar} {value}/25  {status}
→ {recommendation}
```

---

## Status Colors

```javascript
const STATUS_COLORS = {
  thriving: {
    hex: '#00ff00',
    ansi: '\x1b[92m',
    emoji: '🟢'
  },
  stable: {
    hex: '#ffff00',
    ansi: '\x1b[93m',
    emoji: '🟡'
  },
  declining: {
    hex: '#ff9500',
    ansi: '\x1b[33m',
    emoji: '🟠'
  },
  dying: {
    hex: '#ff0000',
    ansi: '\x1b[91m',
    emoji: '🔴'
  }
}
```

---

## Update Frequency

**Recommended intervals:**
- Shell prompt: Every command (via precmd hook)
- tmux status: Every 30s
- IDE statusline: Every 30s
- Notifications: Real-time (subscriptions)
- Dashboard: Every 5s

**Cache strategy:**
```typescript
// Cache status for 30s to avoid excessive reads
let cachedStatus = null
let cacheExpiry = 0

async function getStatus() {
  if (Date.now() < cacheExpiry && cachedStatus) {
    return cachedStatus
  }

  cachedStatus = await mcp.call('reef_get_status')
  cacheExpiry = Date.now() + 30000
  return cachedStatus
}
```

---

## Implementation Checklist

- [ ] Add `reef_get_status` MCP tool
- [ ] Add `reef_format_statusline` MCP tool
- [ ] Add `reef_subscribe_vitality` event stream
- [ ] Implement format templates (minimal/compact/rich/alert)
- [ ] Add shell integrations (zsh/bash/fish)
- [ ] Create VS Code extension
- [ ] Create Raycast extension
- [ ] Document Claude Desktop MCP setup
- [ ] Add color configuration
- [ ] Implement notification thresholds
