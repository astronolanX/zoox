#!/usr/bin/env bash
# Complete the zoox → reef migration
# Run from the reef project root directory

set -e

echo "🐚 Completing reef migration..."
echo

# 1. Rename source directory
echo "1. Renaming src/zoox → src/reef..."
if [ -d "src/zoox" ]; then
    git mv src/zoox src/reef
    echo "   ✓ Directory renamed"
else
    echo "   ⚠ src/zoox not found (may already be renamed)"
fi

# 2. Update imports in test files
echo
echo "2. Updating imports in test files..."
find tests -name "*.py" -type f | while read -r file; do
    if grep -q "from zoox" "$file" || grep -q "import zoox" "$file"; then
        sed -i '' 's/from zoox\./from reef./g' "$file"
        sed -i '' 's/import zoox/import reef/g' "$file"
        echo "   ✓ Updated $file"
    fi
done

# 3. Update imports in source files (if any internal references)
echo
echo "3. Checking for internal zoox references in source..."
if [ -d "src/reef" ]; then
    find src/reef -name "*.py" -type f | while read -r file; do
        if grep -q "zoox" "$file"; then
            sed -i '' 's/zoox/reef/g' "$file"
            echo "   ✓ Updated $file"
        fi
    done
else
    echo "   ⚠ src/reef not found yet"
fi

# 4. Run tests to verify
echo
echo "4. Running tests to verify migration..."
if uv run pytest -x; then
    echo "   ✓ All tests passed!"
else
    echo "   ✗ Tests failed - please review errors"
    exit 1
fi

# 5. Show git status
echo
echo "5. Git status:"
git status --short

echo
echo "✅ Migration complete!"
echo
echo "Next steps:"
echo "  1. Review changes: git diff"
echo "  2. Commit: git add -A && git commit -m 'feat: complete zoox→reef migration'"
echo "  3. Test CLI: uv pip install -e ."
echo "  4. Verify: reef reef  # Should show reef health"
echo
