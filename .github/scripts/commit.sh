#!/usr/bin/env bash
# Usage: commit.sh <message> <pathspec>...
# Commits what changed under the pathspecs and pushes it to main. A push made
# with the workflow's GITHUB_TOKEN starts no other workflow, so a publish
# never triggers itself; app-stream reaches publish through workflow_run.
# The jobs of one run push side by side: a rejected push is rebased and tried
# again.
set -euo pipefail
message=$1
shift
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
for spec in "$@"; do
  # git add refuses a pathspec that matches nothing, such as bundles before the first publish.
  if [ -n "$( git ls-files -co --exclude-standard -- "$spec" | head -1 )" ]; then
    git add -A -- "$spec"
  fi
done
if git diff --cached --quiet; then
  echo "nothing to commit"
  exit 0
fi
git commit -q -m "$message"
for attempt in 1 2 3 4 5 6; do
  if git push -q origin HEAD:main; then
    exit 0
  fi
  sleep $(( RANDOM % 10 + attempt ))
  git pull -q --rebase origin main
done
echo "::error::could not push the commit"
exit 1
