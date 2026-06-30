#!/bin/bash
# cssh — Clean SSH wrapper that strips AMD Conductor banner noise
# Usage: cssh <user@host> '<command>'
# Equivalent to: ssh <user@host> '<command>' | (banner stripped)
#
# The Conductor-managed nodes print a multi-line banner on every SSH:
#   - ASCII AMD logo
#   - "is protected by Conductor SUT Authentication"
#   - "Reminder: An SSH key is required..."
#   - "Checking authorization now..."
# This wrapper runs SSH and strips all of that automatically.

if [ $# -lt 1 ]; then
    echo "Usage: cssh <user@host> [command...]" >&2
    exit 1
fi

ssh -o StrictHostKeyChecking=accept-new "$@" 2>&1 | grep -vE \
    '___.*____|/  \|/  //|/ /\|_/ //|/_/  /_//|Conductor|Reminder:|SSH key|denied access|security groups|conductor\.amd\.com|Checking authorization|help resources|^\s*$' \
    | grep -v '^\s*[•]'
