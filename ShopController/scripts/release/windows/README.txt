快店快点 / Shop Controller - Windows x64 helper

This is the local companion to the GitHub public-beta or Chrome Web Store extension,
not the extension itself. See release-config.json for the package's channel and bound ID.
Supported platform: Windows 11 x64 in a currently vendor-supported servicing release.
1. Fully extract the ZIP.
2. GitHub channel: extract ShopController-extension-unpacked-<version>.zip to a permanent
   folder, open chrome://extensions, enable Developer mode and choose Load unpacked.
   Select the folder containing manifest.json. Keep it for future use. This channel
   uses the fixed public manifest key and does not have Chrome Web Store automatic updates.
   Store channel: install the extension from its official store listing when available.
3. Run Install.cmd. GitHub helpers are already bound to their unpacked extension ID.
   If a store-channel delivery is not bound yet, paste the actual
   32-letter ID shown for Shop Controller in chrome://extensions. Never use another extension's ID.
4. Return to the extension and choose Retry.

The helper installs under %LOCALAPPDATA%\Programs\ShopController and registers only HKCU.
It does not install the extension, create Chrome profiles, copy Cookies, or collect passwords.
Configuration is stored separately under %LOCALAPPDATA%\ShopController and is preserved on uninstall.
An update preserves the previous installation beside the new one. If installation fails, the
installer attempts to restore the previous files and registration. Close the controller during updates.
Uninstall.cmd unregisters only this exact installation and retains files, since the helper may
be running from that directory. After it exits, binaries/backups may be removed manually.

Install.cmd and Uninstall.cmd call explicit modes in the self-contained helper directly;
they do not invoke PowerShell or change its execution policy. The .ps1 files are maintenance
references, not the recommended end-user install path.
This public-beta delivery is unsigned. A system or organisation may block its binary
or restrict developer-mode extensions. Keep device protections and organisation policies enabled.
Signing and clean-machine tests remain future release work, not a claim made by this beta.
No execution-policy bypass is included.
Signing certificates, store approval, and installation on your real Chrome profiles are not implied.
