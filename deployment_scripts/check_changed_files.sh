#!/bin/bash
# Script to check if any files in specified paths have changed
# Usage: check_changed_files.sh <file_patterns>
# Example: check_changed_files.sh "src/onboarder/** src/processor/**"
# Outputs: any_changed=true|false to GITHUB_OUTPUT

set -e

FILE_PATTERNS="$1"

if [ -z "$FILE_PATTERNS" ]; then
  echo "Error: No file patterns specified"
  echo "Usage: check_changed_files.sh <file_patterns>"
  exit 1
fi

echo "Checking for changes in: $FILE_PATTERNS"

# Determine the base ref for comparison
if [ "${{ github.event_name }}" == "pull_request" ]; then
  BASE_REF="${{ github.event.pull_request.base.sha }}"
else
  # For push events, compare with the previous commit
  BASE_REF="${{ github.event.before }}"
fi

# If BASE_REF is empty (e.g., first push), set it to a default
if [ -z "$BASE_REF" ] || [ "$BASE_REF" == "0000000000000000000000000000000000000000" ]; then
  echo "No base ref found, checking all files in current commit"
  BASE_REF="HEAD~1"
fi

echo "Comparing against: $BASE_REF"

# Get the list of changed files
CHANGED_FILES=$(git diff --name-only "$BASE_REF" HEAD 2>/dev/null || true)

if [ -z "$CHANGED_FILES" ]; then
  echo "No changed files detected"
  echo "any_changed=false" >> $GITHUB_OUTPUT
  exit 0
fi

echo "Changed files:"
echo "$CHANGED_FILES"

# Check if any changed file matches the patterns
ANY_CHANGED="false"

# Convert patterns to space-separated list
for PATTERN in $FILE_PATTERNS; do
  # Remove trailing /** if present for better matching
  PATTERN_DIR=$(echo "$PATTERN" | sed 's/\/\*\*$//')
  
  # Check each changed file
  while IFS= read -r FILE; do
    if [ -n "$FILE" ]; then
      # Check if file starts with the pattern directory
      if [[ "$FILE" == "$PATTERN_DIR"* ]]; then
        echo "Match found: $FILE matches pattern $PATTERN"
        ANY_CHANGED="true"
        break
      fi
    fi
  done <<< "$CHANGED_FILES"
  
  if [ "$ANY_CHANGED" == "true" ]; then
    break
  fi
done

echo "any_changed=$ANY_CHANGED" >> $GITHUB_OUTPUT

if [ "$ANY_CHANGED" == "true" ]; then
  echo "Changes detected in specified paths"
else
  echo "No changes detected in specified paths"
fi
