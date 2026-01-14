# Next Session Quick Start

## Immediate Action Required

Run this script to complete the reef migration:

```bash
cd /Users/nolan/Desktop/reef
chmod +x complete-reef-migration.sh
./complete-reef-migration.sh
```

This will:
1. Rename `src/zoox` → `src/reef`
2. Update all imports in test files
3. Run tests to verify
4. Show git status for review

## What Happened This Session (Run 006)

✅ **Fixed 3 High-Priority Bugs:**
- Added XML error handling (prevents crashes on malformed polips)
- Verified subdirectory scanning works correctly
- Completed 90% of zoox→reef rename

✅ **Designed Reef UX Patterns:**
- Session startup menu for polip surfacing
- Modal questions with polip context
- Inline annotations with emoji links
- Constraint violation interrupts
- IDE sidebar panel design
- Cross-touchpoint translation

## Key Files Created

1. **`.claude/runs/run-006.xml`** - Full session documentation
2. **`.claude/contexts/reef-ux-design.blob.xml`** - UX design patterns
3. **`complete-reef-migration.sh`** - Migration script

## Surface These Polips

When starting next session, surface:

```bash
# View reef health
uv run python -m reef.cli reef

# Surface relevant polips
uv run python -m reef.cli index --search "ux design"
uv run python -m reef.cli index --search "migration"
```

Or manually read:
- `.claude/contexts/reef-ux-design.blob.xml` - UX patterns
- `.claude/runs/run-006.xml` - Session summary
- `.claude/constraints/project-rules.blob.xml` - Project constraints

## Next Steps Priority

1. **Complete migration** (5 min)
   ```bash
   ./complete-reef-migration.sh
   ```

2. **Implement SessionStart hook** (30 min)
   - Create `.claude/hooks/session-start.sh`
   - Format `reef surface_relevant` as numbered menu
   - Add 5s timeout with skip default

3. **Add constraint checker** (20 min)
   - Create `.claude/hooks/pre-tool-use.sh`
   - Check Write/Edit tools against bedrock constraints
   - Interrupt with alternatives on violation

4. **Design polip link syntax** (15 min)
   - Test emoji rendering in terminal
   - Implement `(type:name)` clickable format
   - Add to Claude responses

5. **VS Code extension** (2-4 hours)
   - Scaffold extension with tree view
   - Parse `.claude/` directory
   - Display polips grouped by scope
   - Add click-to-open functionality

## Testing After Migration

```bash
# Verify package name
uv pip install -e .

# Test CLI command
reef reef                    # Should show reef health
reef index --search "test"   # Should search polips
reef sprout thread "test"    # Should create polip

# Run full test suite
uv run pytest -v

# Check git status
git status
git diff
```

## Commit Message Template

```
feat: complete zoox→reef migration + add XML error handling

Core Changes:
- Rename package from zoox to reef in pyproject.toml
- Rename src/zoox/ → src/reef/
- Update all imports in tests
- Update documentation (README, CLAUDE.md)
- Update constraint polip

Bug Fixes:
- Add XML error handling with clear ValueError messages (blob.py:437, 516)
- Verify subdirectory scanning includes all 5 directories

Design Work:
- Document 6 UX patterns for polip surfacing
- Design cross-touchpoint translation (terminal/IDE/web)
- Create implementation patterns for hooks

Session Notes: .claude/runs/run-006.xml
UX Design: .claude/contexts/reef-ux-design.blob.xml

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

## Questions to Explore

1. **Should session startup menu be opt-in or opt-out?**
   - Pro opt-in: Less intrusive
   - Pro opt-out: More discoverable
   - Consider: timeout + skip makes opt-out safe

2. **How granular should constraint checking be?**
   - File-level (check entire file)
   - Import-level (check specific imports)
   - Pattern-level (check regex patterns)

3. **IDE extension distribution?**
   - VS Code marketplace
   - Manual install from .claude/extensions/
   - Both?

4. **Polip graph visualization priority?**
   - Terminal (ASCII art)
   - Web interface
   - IDE panel
   - Which first?

## reef as LLM Interface Paradigm

The key insight from this session: **Treat reef as part of Claude's UI, not separate tooling.**

Instead of:
```
User: "Add authentication"
Claude: "Sure, I'll add auth"
[Later] User: "Why did you use sessions? I wanted JWT"
```

With reef:
```
User: "Add authentication"
Claude: [Surfaces polip] "I see you previously decided on JWT (📌deposit:auth-tokens) and have a zero-dependency constraint (⚓bedrock:project-rules). I'll implement JWT using stdlib."
```

Reef becomes **context memory** that prevents repeated decisions and maintains consistency.

---

**Ready to continue? Run the migration script and start with SessionStart hook implementation.**
