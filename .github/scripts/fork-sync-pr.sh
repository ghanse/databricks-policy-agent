#!/usr/bin/env bash
#
# Mirror a PR from the public databricks-policy-agent repo to a branch in the private
# databricks-field-eng mirror and open a test PR there, so the integration tests (which
# need Databricks workspace secrets available only in the mirror) can run against it.
#
# Integration tests are skipped on the public repo — see .github/workflows/ci.yml.
#
# Usage:
#   .github/scripts/fork-sync-pr.sh <PR_NUMBER>
#
# Environment overrides:
#   SOURCE_REPO   owner/repo the PR lives in (default: the `origin` remote's repo)
#   TARGET_REPO   owner/repo to mirror into  (default: databricks-field-eng/databricks-policy-agent)
#
# Prerequisites:
#   - gh CLI installed and authenticated (gh auth login) with access to both repos
#   - Run from a clone of the public databricks-policy-agent repo
#
# First run: creates the fork-test/pr-<N> branch in the mirror and opens a test PR.
# Subsequent runs: force-push the latest changes from the source PR to the same branch.
set -e

TARGET_REPO="${TARGET_REPO:-databricks-field-eng/databricks-policy-agent}"
BASE_BRANCH="main"
TARGET_REMOTE="fork-ci"

if [ -z "$1" ]; then
  echo "Usage: $0 <PR_NUMBER>"
  echo ""
  echo "Example: $0 123"
  echo ""
  echo "Mirrors PR #123 to branch fork-test/pr-123 in $TARGET_REPO,"
  echo "opening a test PR so the integration tests can run with workspace secrets."
  exit 1
fi

PR_NUMBER="$1"
SYNC_BRANCH="fork-test/pr-${PR_NUMBER}"

# Verify we're in a git repo
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "Error: Not in a git repository. Run from a clone of the public databricks-policy-agent repo."
  exit 1
fi

# Verify gh is installed
if ! command -v gh >/dev/null 2>&1; then
  echo "Error: gh CLI is required. Install from https://cli.github.com/"
  exit 1
fi

# The PR lives in the source repo; default to whatever `origin` points at.
if [ -z "${SOURCE_REPO:-}" ]; then
  SOURCE_REPO=$(gh repo view --json nameWithOwner -q '.nameWithOwner' 2>/dev/null || true)
fi
if [ -z "$SOURCE_REPO" ]; then
  echo "Error: could not determine SOURCE_REPO. Set it explicitly, e.g. SOURCE_REPO=ghanse/databricks-policy-agent"
  exit 1
fi

# Capture the initial branch so we can restore it on exit (success or failure).
# `--show-current` is empty in detached-HEAD state; fall back to the commit SHA in that case.
ORIGINAL_REF=$(git branch --show-current)
if [ -z "$ORIGINAL_REF" ]; then
  ORIGINAL_REF=$(git rev-parse HEAD)
fi
trap 'git checkout --quiet "$ORIGINAL_REF" 2>/dev/null || true' EXIT

# Ensure a remote for the mirror exists and points at TARGET_REPO.
if ! git remote get-url "$TARGET_REMOTE" >/dev/null 2>&1; then
  echo "Adding remote $TARGET_REMOTE -> $TARGET_REPO"
  git remote add "$TARGET_REMOTE" "https://github.com/${TARGET_REPO}.git"
fi
TARGET_URL=$(git remote get-url "$TARGET_REMOTE")
if [[ "$TARGET_URL" != *"${TARGET_REPO}"* ]]; then
  echo "Error: remote '$TARGET_REMOTE' does not point to $TARGET_REPO"
  echo "  current: $TARGET_URL"
  echo "  fix with: git remote set-url $TARGET_REMOTE https://github.com/${TARGET_REPO}.git"
  exit 1
fi

# Fetch and checkout the source PR head (handles PRs from forks of the source repo too).
echo "Fetching PR #${PR_NUMBER} from ${SOURCE_REPO}..."
gh pr checkout "$PR_NUMBER" --repo "$SOURCE_REPO"

# Create or update the sync branch and force-push it to the mirror.
git checkout -B "$SYNC_BRANCH"
echo "Pushing to ${TARGET_REMOTE}/${SYNC_BRANCH}..."
git push --force "$TARGET_REMOTE" "HEAD:${SYNC_BRANCH}"

# Make sure the marker labels exist in the mirror (idempotent) before we use them.
gh label create "do-not-merge" --repo "$TARGET_REPO" --color "B60205" --description "Not for merge" --force >/dev/null 2>&1 || true
gh label create "fork-test" --repo "$TARGET_REPO" --color "0E8A16" --description "Mirrored PR for CI" --force >/dev/null 2>&1 || true

# Create the test PR if one does not already exist for this branch.
EXISTING=$(gh pr list --repo "$TARGET_REPO" --head "$SYNC_BRANCH" --state open --json number -q '.[0].number' 2>/dev/null || true)
if [ -z "$EXISTING" ]; then
  PR_URL=$(gh pr view "$PR_NUMBER" --repo "$SOURCE_REPO" --json url -q '.url')
  PR_TITLE=$(gh pr view "$PR_NUMBER" --repo "$SOURCE_REPO" --json title -q '.title')
  TEST_PR_TITLE="Fork test: PR #${PR_NUMBER} - ${PR_TITLE}"
  echo "Creating test PR in ${TARGET_REPO}..."
  gh pr create --repo "$TARGET_REPO" \
    --base "$BASE_BRANCH" \
    --head "$SYNC_BRANCH" \
    --title "$TEST_PR_TITLE" \
    --label "do-not-merge" \
    --label "fork-test" \
    --body "Automated mirror of a public PR for CI testing.

Original PR: ${PR_URL}

Integration tests run on this PR because it lives in the private mirror where the
Databricks workspace secrets are configured. They are skipped on the public repo."
  echo "Test PR created."
else
  echo "Test PR already exists: #${EXISTING}"
  echo "Branch ${SYNC_BRANCH} has been updated with the latest changes from PR #${PR_NUMBER}."
fi
