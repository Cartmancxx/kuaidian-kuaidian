快店快点 / Shop Controller - macOS native helper

This is a companion to the GitHub public-beta or Chrome Web Store extension. It keeps all shop pages in native
Google Chrome. On Mac the controller is an ordinary independent window, not always-on-top.

Requires macOS 15 or newer in a currently vendor-supported release. Choose osx-arm64 for Apple Silicon, osx-x64 for Intel.
For the GitHub channel, first extract ShopController-extension-unpacked-<version>.zip
to a permanent folder. In chrome://extensions, enable Developer mode, choose Load unpacked
and select the folder containing manifest.json. The helper is already bound to the ID
derived from the public manifest key. There is no Chrome Web Store automatic update in this channel.
For the store channel, install from its official store listing when available.
Fully extract the helper ZIP, then run
Install.command. If the package is not yet bound to its official store ID, enter the real
Shop Controller ID displayed in chrome://extensions. The installer registers only that ID.
No sudo, Python, Node, .NET installation, or Chrome profile editing is required.

The helper lives in ~/Library/Application Support/ShopController/host.
The Chrome host manifest lives in
~/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.shopcontroller.chrome.json.
Shop configuration is separate and survives updates and uninstall.
Updates preserve the previous host; a failed install attempts to restore it.
Uninstall.command removes only the matching registration and archives installed binaries.
It does not remove Cookie databases, passwords, Chrome profiles, or the extension.

PUBLIC DISTRIBUTION STATUS
This build produced on Windows is unsigned, not notarized, and not Mac-runtime tested.
macOS or an organisation may block untrusted software. Keep system protections enabled.
The publisher still needs signing/notarization and real Intel/Apple Silicon Mac tests before claiming
a frictionless stable release. These limitations remain explicit in the GitHub public beta.
Developer mode may also be restricted by organisation policies. Do not bypass those policies.
Sign-And-Notarize.sh is a publisher tool requiring the
publisher's own Developer ID and notarytool keychain profile; it is never run automatically.

Installed files have owner-only permissions. Uninstall/update backup directories may be
removed manually after confirming they are no longer needed; config.json is retained.
