# Reviewer instructions — 快店快点 / Kuai Dian Kuai Dian

Publisher: 程大意. Contact: cartmancxx@gmail.com.

## Channel status and prerequisites
The extension is published in Chrome Web Store: https://chromewebstore.google.com/detail/快店快点/ckeiapojbffhmmedjajdbnpfongmfjmm . Its store ID is ckeiapojbffhmmedjajdbnpfongmfjmm. The store page shows version 1.0.0 and an update date of 2026-10-29. This repository remains MIT-licensed. These instructions also support subsequent update reviews.

This extension requires a separately installed native messaging helper. Store-bound helpers are published in https://github.com/Cartmancxx/kuaidian-kuaidian/releases/tag/v1.0.0-store.1 . The public setup and download page is https://cartmancxx.github.io/kuaidian-kuaidian/ and the privacy policy is https://cartmancxx.github.io/kuaidian-kuaidian/privacy.html . Chrome Web Store publication of the extension does not certify the separately distributed helper or its OS installation/signing status.

The historical GitHub v1.0.0 unpacked extension has a different ID, hadeebhijljjdebkaiaglaeipajnnind. Its helpers bind only to that ID. A user migrating to the store extension must disable the old extension and install the new store-bound helper, explicitly authorizing the identity replacement: run `Install.cmd --replace-identity` on Windows (`.\Install.cmd --replace-identity` in PowerShell), or `./Install.command --replace-identity` on Mac, from the extracted package directory. A normal reinstall refuses an identity conflict; it does not silently rebind. Back up `config.json` and its existing `.bak` before migrating. Local shop configuration is retained; Chrome profiles and cookies are untouched. Do not use the old helper package with the store extension.

Current helpers are unsigned and not notarized. macOS builds were cross-compiled and have not passed real-Mac execution acceptance. Real Chrome integration, Windows topmost behavior, and cross-profile GPT control are not yet verified. System policy can block execution; these instructions do not ask reviewers to disable protections.

Supported targets: vendor-supported Windows 11 x64; macOS 15 and later versions supported by .NET 10 on Apple Silicon or Intel; Google Chrome 116+ (current stable recommended). macOS has no always-on-top feature.

## What the extension does
A compact launcher stores shop entries and routes their URLs into existing, user-selected native Chrome profiles. It does not read, export, switch or inject cookies. It does not detect the actual logged-in merchant identity. It has no account registration or paid login to its own service. It requests only nativeMessaging and storage, without host permissions or content scripts.

## Test without merchant credentials
1. Install the extension from the review build. Open its toolbar icon, then the connection/setup link or Options page.
2. Install the matching helper from the published download URL. If prompted, copy the actual extension ID shown by the setup page. Both native host allowed_origins and host-identity.json must match this exact ID.
3. Confirm the setup page shows helper version 1.0.0, the correct OS, and connected state.
4. In Chrome, create two disposable local profiles named Review A and Review B. Open each once, then close those test windows if desired. No merchant login is required.
5. In the extension's management page, refresh profile information. Add two shop entries under Other: Review A and Review B, each with a distinct account alias and https://example.com/ as its URL. Bind each to its namesake Chrome profile.
6. Open the compact launcher from the toolbar. Search for one entry, click it, and confirm native Chrome opens the public example page in the expected profile. Return to the small launcher and open the other entry. The message means launch requested, not login verified. Repeated clicks may open new tabs.
7. Windows: in a real extension-created popup, the launcher requests always-on-top once; the pin toggle can cancel it. Focus changes alone must not re-pin a manually unpinned window. macOS: the pin control is hidden and no pin command is sent.
8. Edit/delete a test shop and refresh the launcher. Pairing suggestions require selecting allowed profiles and previewing before applying. A plan changes bindings only; it does not migrate sessions or delete profiles.
9. To exercise disconnect handling, uninstall the helper using its supplied uninstaller, leaving extension and configuration. Refresh: setup guidance is visible, with no fabricated shop or login state. Reinstall/recheck restores connectivity. Uninstallation retains helper binaries (archived on macOS) and shop configuration; remove test configuration separately if desired.

## Actual merchant pages
Optional merchant login requires the reviewer's own test accounts and normal platform authentication. The extension never requests account passwords, tokens, cookies or bypasses platform login. Profile routing can be tested fully on the public example page above.

## Implementation notes
The MV3 background worker accepts a fixed action allowlist only from this extension's own pages. Native messaging is length-framed JSON. The host validates its bound origin and fixed action schema; launch uses ProcessStartInfo.ArgumentList. Windows pin calls are sent directly by the popup so Chrome supplies the parent-window argument. There is no downloaded JS, embedded browser, debug port, telemetry or hidden production demo mode.

## Cleanup
Close the launcher, uninstall the helper, then remove the extension. The installer/uninstaller never deletes Chrome profiles or their login data. Test configuration and its .bak can be removed separately from %LOCALAPPDATA%\ShopController on Windows or ~/Library/Application Support/ShopController on Mac. Old helper versions may remain archived for rollback.

