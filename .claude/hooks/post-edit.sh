#!/bin/bash
# Post-edit hook: auto-lint and auto-test after file edits
# Runs ruff on edited Python files and executes matching unit tests

FILE_PATH="$1"

if [[ -z "$FILE_PATH" ]]; then
    exit 0
fi

# Only process Python files
if [[ "$FILE_PATH" != *.py ]]; then
    exit 0
fi

# Auto-format with ruff
if command -v ruff &> /dev/null; then
    ruff format "$FILE_PATH" 2>/dev/null
    ruff check --fix "$FILE_PATH" 2>/dev/null
fi

# Find and run matching unit test
BASENAME=$(basename "$FILE_PATH" .py)
DIR=$(dirname "$FILE_PATH")

# Look for test file in nearby unittests/ directory
TEST_FILE=""
if [[ -f "${DIR}/unittests/test_${BASENAME}.py" ]]; then
    TEST_FILE="${DIR}/unittests/test_${BASENAME}.py"
elif [[ -f "${DIR}/../unittests/test_${BASENAME}.py" ]]; then
    TEST_FILE="${DIR}/../unittests/test_${BASENAME}.py"
fi

if [[ -n "$TEST_FILE" ]]; then
    echo "[post-edit] Running tests: $TEST_FILE"
    pytest "$TEST_FILE" -q --tb=short 2>/dev/null
fi

# Warn if file exceeds 500 lines
LINE_COUNT=$(wc -l < "$FILE_PATH" 2>/dev/null)
if [[ "$LINE_COUNT" -gt 500 ]]; then
    echo "[post-edit] WARNING: $FILE_PATH is $LINE_COUNT lines (limit: 500). Consider splitting."
fi

exit 0
