#!/bin/bash
set -euo pipefail
SOURCE="$(cd -P "$(dirname "$0")" && pwd)"
# shellcheck source=Common.sh
. "$SOURCE/Common.sh"
require_mac
MACOS_VERSION="$(/usr/bin/sw_vers -productVersion)"
MACOS_MAJOR="${MACOS_VERSION%%.*}"
[[ "$MACOS_MAJOR" =~ ^[0-9]+$ ]] && [ "$MACOS_MAJOR" -ge 15 ] || fail 'This .NET 10 helper requires macOS 15 or newer.'
product_paths
assert_no_symlink "$SOURCE"
EXTENSION_ID=''
REPLACE_IDENTITY=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --extension-id) [ "$#" -ge 2 ] || fail 'Missing extension ID.'; EXTENSION_ID="$2"; shift 2 ;;
    --replace-identity) REPLACE_IDENTITY=1; shift ;;
    *) fail "Unknown installer option: $1" ;;
  esac
done
[ "$(json_field "$SOURCE/release-config.json" product)" = ShopController ] || fail 'Invalid release package.'
RUNTIME="$(json_field "$SOURCE/release-config.json" runtime)"
VERSION="$(json_field "$SOURCE/release-config.json" version)"
[[ "$VERSION" =~ ^[0-9]+(\.[0-9]+){1,3}$ ]] || fail 'Invalid version metadata.'
ARCH="$(/usr/bin/uname -m)"
# A translated Terminal may report x86_64 on an Apple Silicon Mac.
ARM_CAPABLE="$(/usr/sbin/sysctl -n hw.optional.arm64 2>/dev/null || printf '0')"
case "$RUNTIME" in
  osx-arm64) [ "$ARCH" = arm64 ] || [ "$ARM_CAPABLE" = 1 ] || fail 'This download requires Apple Silicon.' ;;
  osx-x64) [ "$ARCH" = x86_64 ] || fail 'Use the Apple Silicon download on this Mac.' ;;
  *) fail 'This package is not a macOS helper.' ;;
esac
BOUND_ID="$(json_field "$SOURCE/release-config.json" extensionId)"
if [ -n "$BOUND_ID" ]; then
  [ -z "$EXTENSION_ID" ] || [ "$EXTENSION_ID" = "$BOUND_ID" ] || fail 'The package is bound to a different extension ID.'
  EXTENSION_ID="$BOUND_ID"
fi
if [ -z "$EXTENSION_ID" ]; then
  printf 'Paste the actual Shop Controller ID shown in chrome://extensions: '
  IFS= read -r EXTENSION_ID
fi
validate_id "$EXTENSION_ID"
[ -f "$SOURCE/host/ShopController.Host" ] || fail 'Extract the complete release ZIP before installing.'
[ -z "$(/usr/bin/find "$SOURCE/host" -type l -print -quit)" ] || fail 'The helper package contains a symbolic link.'
if [ -e "$HOST_DIR" ]; then
  [ -d "$HOST_DIR" ] && [ -f "$HOST_DIR/.shopcontroller-install" ] || fail 'Existing host directory has no product marker; preserved.'
  OLD_ID="$(json_field "$HOST_DIR/host-identity.json" extensionId)"
  [ "$OLD_ID" = "$EXTENSION_ID" ] || [ "$REPLACE_IDENTITY" = 1 ] || fail 'Existing helper uses another ID. Confirm migration and run with --replace-identity.'
fi
assert_existing_manifest_owned
umask 077
/bin/mkdir -p "$PRODUCT" "$MANIFEST_DIR"
# Restrict only our own product directory, never Chrome, Library, or other user directories.
/bin/chmod 700 "$PRODUCT"
LOCK="$PRODUCT/.install.lock"
/bin/mkdir "$LOCK" 2>/dev/null || fail 'Another installation is running. If a prior run crashed, inspect the empty .install.lock directory before removing it.'
STAMP="$(/bin/date '+%Y%m%d-%H%M%S')-$$"
STAGE="$PRODUCT/.host-stage-$STAMP"
BACKUP="$PRODUCT/host.previous-$STAMP"
FAILED="$PRODUCT/host.failed-$STAMP"
MANIFEST_TEMP="$MANIFEST_DIR/.shopcontroller-$STAMP.tmp"
MANIFEST_BACKUP="$PRODUCT/native-manifest.previous-$STAMP.json"
for PATH_TO_CREATE in "$STAGE" "$BACKUP" "$FAILED" "$MANIFEST_TEMP" "$MANIFEST_BACKUP"; do
  assert_no_symlink "$PATH_TO_CREATE"
  [ ! -e "$PATH_TO_CREATE" ] || fail 'A staging or backup target already exists.'
done
MOVED_OLD=0
MOVED_NEW=0
HAD_MANIFEST=0
COMMITTED=0
cleanup() {
  local code=$?
  set +e
  if [ "$COMMITTED" != 1 ]; then
    if [ "$MOVED_NEW" = 1 ] && [ -d "$HOST_DIR" ] && [ ! -L "$HOST_DIR" ]; then /bin/mv "$HOST_DIR" "$FAILED"; fi
    if [ "$MOVED_OLD" = 1 ] && [ -d "$BACKUP" ] && [ ! -L "$BACKUP" ]; then /bin/mv "$BACKUP" "$HOST_DIR"; fi
    if [ "$HAD_MANIFEST" = 1 ] && [ -f "$MANIFEST_BACKUP" ]; then /bin/cp "$MANIFEST_BACKUP" "$MANIFEST"; fi
  fi
  [ ! -f "$MANIFEST_TEMP" ] || /bin/rm "$MANIFEST_TEMP"
  /bin/rmdir "$LOCK" 2>/dev/null
  exit "$code"
}
trap cleanup EXIT
/bin/mkdir "$STAGE"
/bin/cp -R "$SOURCE/host/." "$STAGE/"
/usr/bin/find "$STAGE" -type d -exec /bin/chmod 700 {} +
/usr/bin/find "$STAGE" -type f -exec /bin/chmod 600 {} +
/bin/chmod 700 "$STAGE/ShopController.Host"
printf 'ShopController %s\n' "$VERSION" > "$STAGE/.shopcontroller-install"
printf '{"extensionId":"%s"}\n' "$EXTENSION_ID" > "$STAGE/host-identity.json"
for FILE in Common.sh Uninstall.command README.txt release-config.json; do
  assert_no_symlink "$PRODUCT/$FILE"
  /bin/cp "$SOURCE/$FILE" "$PRODUCT/$FILE"
done
/bin/mkdir -p "$STAGE/runtime-notices"
/bin/cp "$SOURCE/runtime-notices/LICENSE.txt" "$SOURCE/runtime-notices/ThirdPartyNotices.txt" "$STAGE/runtime-notices/"
/bin/chmod 700 "$PRODUCT/Uninstall.command" "$PRODUCT/Common.sh"
if [ -e "$MANIFEST" ]; then /bin/cp "$MANIFEST" "$MANIFEST_BACKUP"; HAD_MANIFEST=1; fi
printf '{\n "name":"com.shopcontroller.chrome",\n "description":"Shop Controller native profile launcher",\n "path":"%s",\n "type":"stdio",\n "allowed_origins":["chrome-extension://%s/"]\n}\n' "$(json_escape "$HOST_EXE")" "$EXTENSION_ID" > "$MANIFEST_TEMP"
if [ -d "$HOST_DIR" ]; then
  assert_no_symlink "$HOST_DIR"
  /bin/mv "$HOST_DIR" "$BACKUP"
  MOVED_OLD=1
fi
assert_no_symlink "$STAGE"
/bin/mv "$STAGE" "$HOST_DIR"
MOVED_NEW=1
/bin/mv "$MANIFEST_TEMP" "$MANIFEST"
COMMITTED=1
printf '\nInstalled Shop Controller %s for this user.\nAllowed extension: %s\nReturn to the extension and choose Retry.\n' "$VERSION" "$EXTENSION_ID"
printf 'No Chrome profile, Cookie, password, or system protection was changed.\n'
if [ "$MOVED_OLD" = 1 ]; then printf 'Previous host files retained: %s\n' "$BACKUP"; fi
