#!/usr/bin/env bash
# Usage: process.sh check <manifest>...
set -uo pipefail

mode=$1
shift
[ "$mode" = "check" ] || { echo "process.sh only checks; publishing is tools/publish.py" >&2; exit 2; }
root=$(cd "$(dirname "$0")/../.." && pwd)
work=${RUNNER_TEMP:-$(mktemp -d)}
failed=0

bundle_entry() {
  local manifest=$1 channel
  rm -f "$work/bundle.zip" "$work/bundle.json"
  for channel in release dev; do
    if BUNDLE_SDK_CHANNEL=$channel python3 "$root/tools/bundle.py" --nolint \
        --json-manifest "$work/bundle.json" "$manifest" "$work/bundle.zip"; then
      return 0
    fi
    echo "::warning file=$manifest::bundle failed with the $channel SDK"
  done
  return 1
}

version_is_new() {
  local manifest=$1 id version code
  [ -n "${QU_CATALOG_URL:-}" ] || return 0
  id=$(jq -r '.id' "$work/bundle.json")
  version=$(jq -r '.version' "$work/bundle.json")
  code=$(curl -sw '%{http_code}' -o /dev/null "$QU_CATALOG_URL/api/v0/application/$id/versions?version=$version")
  if [ "$code" != "404" ]; then
    echo "::error file=$manifest::version $version of $id already exists (or the server failed, code $code)"
    return 1
  fi
}

for manifest in "$@"; do
  echo "::group::$manifest"
  case "$manifest" in
    animations/*)
      python3 "$root/tools/publish.py" "$mode" "$manifest" || failed=1
      ;;
    applications/*|menustyles/*)
      if ! bundle_entry "$manifest"; then
        echo "::error file=$manifest::bundle failed"
        failed=1
      else
        case "$manifest" in
          applications/*) version_is_new "$manifest" || failed=1 ;;
        esac
      fi
      ;;
    *)
      echo "::warning file=$manifest::not a catalog manifest, skipped"
      ;;
  esac
  echo "::endgroup::"
done

exit $failed
