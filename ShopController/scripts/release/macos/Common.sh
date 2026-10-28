#!/bin/bash
# Shared installation helpers; no browser automation or credential access.
set -euo pipefail

fail() { printf '%s\n' "$*" >&2; exit 1; }
require_mac() { [ "$(/usr/bin/uname -s)" = Darwin ] || fail 'This installer is for macOS only.'; }
reject_controls() {
  if printf '%s' "$1" | LC_ALL=C /usr/bin/grep -q '[[:cntrl:]]'; then fail 'Control characters in a path are not accepted.'; fi
}
assert_no_symlink() {
  local path="$1" current='' rest part
  reject_controls "$path"
  case "$path" in /*) ;; *) fail 'An absolute path is required.' ;; esac
  rest="${path#/}"
  while [ -n "$rest" ]; do
    part="${rest%%/*}"
    case "$part" in ''|.|..) fail 'Non-canonical path component rejected.' ;; esac
    current="$current/$part"
    [ ! -L "$current" ] || fail "A redirected path was preserved: $current"
    if [ "$rest" = "$part" ]; then rest=''; else rest="${rest#*/}"; fi
  done
}
json_field() {
  # Foundation JSON parsing is built into macOS; no Python/Node dependency.
  /usr/bin/osascript -l JavaScript - "$1" "$2" <<'JXA'
ObjC.import('Foundation');
function run(args) {
  const data = $.NSString.stringWithContentsOfFileEncodingError(args[0], $.NSUTF8StringEncoding, null);
  if (!data) throw new Error('Unreadable JSON metadata');
  const value = JSON.parse(ObjC.unwrap(data))[args[1]];
  if (value === null || value === undefined) return '';
  if (typeof value !== 'string') throw new Error('Expected string metadata');
  return value;
}
JXA
}
json_escape() {
  local value="$1"
  reject_controls "$value"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  printf '%s' "$value"
}
validate_id() { [[ "$1" =~ ^[a-p]{32}$ ]] || fail 'The actual Chrome extension ID must contain 32 lowercase letters a-p.'; }
product_paths() {
  [ -n "${HOME:-}" ] || fail 'HOME is missing.'
  assert_no_symlink "$HOME"
  SUPPORT="$HOME/Library/Application Support"
  PRODUCT="$SUPPORT/ShopController"
  HOST_DIR="$PRODUCT/host"
  HOST_EXE="$HOST_DIR/ShopController.Host"
  MANIFEST_DIR="$SUPPORT/Google/Chrome/NativeMessagingHosts"
  MANIFEST="$MANIFEST_DIR/com.shopcontroller.chrome.json"
  assert_no_symlink "$PRODUCT"
  assert_no_symlink "$MANIFEST"
}
assert_existing_manifest_owned() {
  if [ -e "$MANIFEST" ]; then
    [ -f "$MANIFEST" ] || fail 'The manifest path is not a regular file.'
    [ "$(json_field "$MANIFEST" name)" = 'com.shopcontroller.chrome' ] || fail 'An unrelated manifest exists and was preserved.'
    [ "$(json_field "$MANIFEST" path)" = "$HOST_EXE" ] || fail 'The native host is registered to another path; uninstall that registration first.'
  fi
}
