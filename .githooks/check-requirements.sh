#!/bin/bash
# CRITICAL: Prevent requirements.new.txt from being committed

if git diff --cached --name-only | grep -q "requirements.new.txt"; then
    echo "❌ ERROR: requirements.new.txt detected!"
    echo "❌ This file causes deployment failures!"
    echo "❌ Only requirements.txt should exist!"
    echo ""
    echo "Fix: git rm requirements.new.txt"
    exit 1
fi

# Check for duplicate requirements files
req_count=$(ls requirements*.txt 2>/dev/null | wc -l)
if [ "$req_count" -gt 1 ]; then
    echo "❌ ERROR: Multiple requirements files detected:"
    ls requirements*.txt
    echo ""
    echo "Only requirements.txt should exist!"
    exit 1
fi

echo "✅ Requirements check passed"
exit 0
