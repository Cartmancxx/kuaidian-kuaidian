#!/bin/bash
set -euo pipefail
SOURCE="$(cd -P "$(dirname "$0")" && pwd)"
. "$SOURCE/Common.sh"
require_mac
product_paths
assert_existing_manifest_owned
if [ -e "$HOST_DIR" ]; then
  [ -d "$HOST_DIR" ] && [ -f "$HOST_DIR/.shopcontroller-install" ] || fail 'Unmarked host directory preserved; no registration changed.'
fi
if [ ! -d "$PRODUCT" ]; then printf 'No Shop Controller helper installation found.\n'; exit 0; fi
LOCK="$PRODUCT/.install.lock"
/bin/mkdir "$LOCK" 2>/dev/null || fail 'Another installation or uninstall is running.'
trap '/bin/rmdir "$LOCK" 2>/dev/null || true' EXIT
STAMP="$(/bin/date '+%Y%m%d-%H%M%S')-$$"
MANIFEST_ARCHIVE="$PRODUCT/native-manifest.uninstalled-$STAMP.json"
HOST_ARCHIVE="$PRODUCT/host.uninstalled-$STAMP"
for ARCHIVE in "$MANIFEST_ARCHIVE" "$HOST_ARCHIVE"; do
  assert_no_symlink "$ARCHIVE"
  [ ! -e "$ARCHIVE" ] || fail 'An uninstall archive already exists; preserved.'
done
if [ -f "$MANIFEST" ]; then
  assert_no_symlink "$MANIFEST"
  /bin/mv "$MANIFEST" "$MANIFEST_ARCHIVE"
fi
if [ -d "$HOST_DIR" ]; then
  assert_no_symlink "$HOST_DIR"
  /bin/mv "$HOST_DIR" "$HOST_ARCHIVE"
fi
printf 'Helper registration removed; binaries archived for recovery.\n'
printf 'Shop configuration and all Chrome data remain unchanged. Remove the extension separately in Chrome if desired.\n'
