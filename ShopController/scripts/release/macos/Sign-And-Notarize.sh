#!/bin/bash
# Publisher-only, run on a Mac after extraction. Never removes quarantine or disables Gatekeeper.
set -euo pipefail
ROOT="$(cd -P "$(dirname "$0")" && pwd)"
[ "$(/usr/bin/uname -s)" = Darwin ] || { printf 'Run this publisher tool on macOS.\n' >&2; exit 1; }
: "${DEVELOPER_ID_APPLICATION:?Set the full Developer ID Application signing identity}"
: "${NOTARY_KEYCHAIN_PROFILE:?Set an existing notarytool keychain-profile name}"
[ -f "$ROOT/host/ShopController.Host" ] || { printf 'Missing helper binary.\n' >&2; exit 1; }
[ -z "$(/usr/bin/find "$ROOT/host" -type l -print -quit)" ] || { printf 'Symbolic links in helper payload are rejected.\n' >&2; exit 1; }
ENTITLEMENTS="$ROOT/.signing-entitlements.plist"
cat > "$ENTITLEMENTS" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>com.apple.security.cs.allow-jit</key><true/></dict></plist>
PLIST
while IFS= read -r -d '' FILE; do
  if /usr/bin/file "$FILE" | /usr/bin/grep -q 'Mach-O'; then
    /usr/bin/codesign --force --options runtime --timestamp --entitlements "$ENTITLEMENTS" --sign "$DEVELOPER_ID_APPLICATION" "$FILE"
    /usr/bin/codesign --verify --strict --verbose=2 "$FILE"
  fi
done < <(/usr/bin/find "$ROOT/host" -type f -print0)
ARCHIVE="${ROOT}.signed.zip"
[ ! -e "$ARCHIVE" ] || { printf 'Signed archive already exists; choose a clean release folder.\n' >&2; exit 1; }
/usr/bin/ditto -c -k --keepParent "$ROOT" "$ARCHIVE"
RESULT="${ARCHIVE}.notary-result.json"
/usr/bin/xcrun notarytool submit "$ARCHIVE" --keychain-profile "$NOTARY_KEYCHAIN_PROFILE" --wait --output-format json > "$RESULT"
. "$ROOT/Common.sh"
[ "$(json_field "$RESULT" status)" = Accepted ] || { printf 'Apple did not accept this submission. Inspect %s\n' "$RESULT" >&2; exit 1; }
printf '\nApple accepted this notarization submission. Keep the JSON result as release evidence.\n'
printf 'A ZIP/raw executable has no staple target. For offline tickets, prepare a signed PKG or DMG on Mac and staple that container.\n'
printf 'Test installation and first Chrome launch on clean Macs under normal Gatekeeper settings before publishing.\n'
