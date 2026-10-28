"""Normal-mode Native Messaging identity tests in an isolated copied host directory.

Only get_capabilities is sent. No installed host, browser profile, registry, window,
Cookie, or real configuration is accessed. The program is never launched with an
open-shop or mutation request.
"""
from __future__ import annotations

import json
import argparse
import shutil
import struct
import subprocess
import tempfile
import time
from pathlib import Path

from protocol_tests import DOTNET, DLL, PROJECT, REPO, check


class RetryingTemporaryDirectory(tempfile.TemporaryDirectory):
    """Retry test-only cleanup when Windows denies access after process exit."""
    def cleanup(self):
        for attempt in range(20):
            try:
                return super().cleanup()
            except OSError:
                if attempt == 19:
                    # Preserve evidence rather than hiding assertion failures or deleting
                    # outside the temporary directory when cleanup remains denied.
                    print("WARN Windows denied test-only cleanup; retained:", self.name)
                    return
                time.sleep(0.1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-build", action="store_true")
    args = parser.parse_args()
    if not args.no_build:
        subprocess.run([str(DOTNET), "build", str(PROJECT), "-c", "Release"], cwd=REPO, check=True)
    body = json.dumps({"action": "get_capabilities"}).encode()
    frame = struct.pack("<I", len(body)) + body
    accepted_id = "abcdefghijklmnopabcdefghijklmnop"
    origin = f"chrome-extension://{accepted_id}/"
    count = 0

    with RetryingTemporaryDirectory(prefix="ShopController.Identity.") as temporary:
        root = Path(temporary)
        # Framework-dependent build outputs only; never reuse the real install folder.
        for item in DLL.parent.iterdir():
            if item.is_file():
                shutil.copy2(item, root / item.name)
        local_dll = root / DLL.name
        identity = root / "host-identity.json"

        def invoke(caller: str):
            return subprocess.run([str(DOTNET), str(local_dll), caller], input=frame,
                capture_output=True, timeout=12, cwd=root,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

        def deny(name: str, caller: str = origin):
            nonlocal count
            result = invoke(caller)
            check(result.returncode == 2, name + " must fail closed with origin-validation exit code")
            check(result.stdout == b"", name + " must not write non-protocol output")
            count += 1
            print("PASS ", name)

        deny("missing sidecar does not fall back to the development ID")
        for name, content in [
            ("malformed identity", "{"),
            ("null identity", "null"),
            ("missing extension ID", "{}"),
            ("unknown identity property", json.dumps({"extensionId": accepted_id, "allowAll": True})),
            ("duplicate identity property", '{"extensionId":"' + accepted_id + '","extensionId":"' + accepted_id + '"}'),
            ("non-string identity property", json.dumps({"extensionId": 123})),
            ("case-sensitive property name", json.dumps({"ExtensionId": accepted_id})),
            ("invalid alphabet", json.dumps({"extensionId": "z" * 32})),
            ("short extension ID", json.dumps({"extensionId": "a" * 31})),
            ("case-sensitive extension ID", json.dumps({"extensionId": "A" * 32})),
            ("URL instead of ID", json.dumps({"extensionId": origin})),
        ]:
            identity.write_text(content, encoding="utf-8")
            deny(name)

        identity.write_text(json.dumps({"extensionId": accepted_id}), encoding="utf-8")
        for name, caller in [
            ("wrong extension", "chrome-extension://" + "p" * 32 + "/"),
            ("development extension is not implicitly trusted", "chrome-extension://hadeebhijljjdebkaiaglaeipajnnind/"),
            ("origin missing terminal slash", origin[:-1]),
            ("origin with page path", origin + "popup.html"),
            ("origin with query string", origin + "?x=1"),
            ("foreign scheme", origin.replace("chrome-extension", "https")),
        ]:
            deny(name, caller)

        result = invoke(origin)
        check(result.returncode == 0, "Exact configured origin should work: " + result.stderr.decode(errors="replace"))
        check(len(result.stdout) >= 4, "Accepted origin must return a Native Messaging frame")
        length = struct.unpack("<I", result.stdout[:4])[0]
        check(length == len(result.stdout) - 4, "Only one complete response frame is expected")
        reply = json.loads(result.stdout[4:])
        check(reply.get("ok") is True, "Capability handshake must succeed without profile discovery")
        capability = reply["data"]
        check(capability["hostVersion"] == "1.0.0", "Published host version should be reported")
        check(capability["protocolVersion"] == 1, "Protocol version should be reported")
        check(capability["platform"] in ("windows", "macos", "unsupported"), "Explicit platform capability")
        check(isinstance(capability["capabilities"]["pin"], bool), "Pin capability must be a boolean")
        check(not (root / "config.json").exists(), "Handshake must not create a configuration")
        count += 1
        print("PASS  exact configured origin receives versioned capabilities without browser access")

    print(f"\n{count}/{count} isolated identity checks passed; no browser or installed host was accessed.")


if __name__ == "__main__":
    main()
