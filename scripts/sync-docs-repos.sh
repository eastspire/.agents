#!/usr/bin/env bash
# sync-docs-repos.sh
# Pulls latest code for the three documentation-source repos and emits a
# one-line-per-repo summary the cron agent can read. Runs idempotently:
#   - If ~/.cache/docs-update/<repo>/.git exists -> fetch + reset --hard to
#     origin/<default-branch>.
#   - Otherwise -> fresh shallow clone.
#
# Designed for Windows / git-bash / msys. Uses `cd dir && git ...` rather
# than `git -C dir` because some Windows / msys path lookups get out of
# sync after fresh clones (bash sees no entry, git sees one, neither
# agrees — `git -C` then errors with "cannot change to"). Going through
# the shell's cd avoids the lookup race entirely.
#
# Exit codes:
#   0  every repo synced cleanly
#   1  one or more repos failed (errors already printed to stderr)
set -u

CACHE_ROOT="/c/Users/14915/.cache/docs-update"
BACKUP_DIR="${CACHE_ROOT}/_backup_user_dump"
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
LOG_PREFIX="[sync-docs ${TIMESTAMP}]"

REPOS=(
  "euv|https://github.com/euv-dev/euv.git"
  "euv-app|https://github.com/euv-dev/euv-app"
  "hyperlane|https://github.com/hyperlane-dev/hyperlane.git"
)

mkdir -p "${CACHE_ROOT}"

echo "${LOG_PREFIX} cache=${CACHE_ROOT}"
echo "${LOG_PREFIX} backup_user_dump=${BACKUP_DIR} (preserved, not touched)"

OVERALL_RC=0

for entry in "${REPOS[@]}"; do
  name="${entry%%|*}"
  url="${entry##*|}"
  dir="${CACHE_ROOT}/${name}"
  echo
  echo "================================================================"
  echo "${LOG_PREFIX} ${name} -> ${dir}"
  echo "================================================================"

  if [ -d "${dir}/.git" ]; then
    echo "[${name}] existing clone, fetching..."
    (
      cd "${dir}" && git fetch --depth 50 origin 2>&1 | tail -3
    ) || {
      echo "[${name}] fetch FAILED" >&2
      OVERALL_RC=1
      continue
    }
    # Pick the default branch from origin/HEAD
    default_branch="$(cd "${dir}" && git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||')"
    if [ -z "${default_branch}" ]; then
      default_branch="main"
      if cd "${dir}" && git show-ref --verify --quiet refs/remotes/origin/master; then
        default_branch="master"
      fi
    fi
    echo "[${name}] resetting to origin/${default_branch}"
    (
      cd "${dir}" && git reset --hard "origin/${default_branch}" 2>&1 | tail -3
    ) || {
      echo "[${name}] reset FAILED" >&2
      OVERALL_RC=1
      continue
    }
  else
    # Directory exists but isn't a git repo -> blow it away and re-clone,
    # unless the directory name matches our preserved backup.
    if [ -d "${dir}" ] && [ "${dir}" != "${BACKUP_DIR}" ]; then
      echo "[${name}] non-git directory exists, removing"
      rm -rf "${dir}"
    fi
    echo "[${name}] cloning ${url}"
    git clone --depth 50 "${url}" "${dir}" 2>&1 | tail -5 || {
      echo "[${name}] clone FAILED" >&2
      OVERALL_RC=1
      continue
    }
  fi

  head_sha="$(cd "${dir}" && git rev-parse HEAD)"
  head_short="$(cd "${dir}" && git rev-parse --short HEAD)"
  head_msg="$(cd "${dir}" && git log -1 --pretty=%s)"
  echo "[${name}] HEAD=${head_short} ${head_msg}"
  echo "[${name}] url=${url}"
  echo "[${name}] path=${dir}"
done

echo
echo "${LOG_PREFIX} done rc=${OVERALL_RC}"
exit "${OVERALL_RC}"