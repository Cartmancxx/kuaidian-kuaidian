"""Run only get_capabilities from the Windows release payload in a temporary directory.

Never executes installer commands, registers a host, or sends profile/configuration actions.
The bundle extraction cache is also restricted to this test's temporary directory.
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import subprocess
import zipfile
from pathlib import Path, PurePosixPath

from distribution_tests import safe_names
from identity_tests import RetryingTemporaryDirectory
from protocol_tests import check


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("release_directory", type=Path)
    args = parser.parse_args()
    if os.name != "nt":
        print("SKIP Windows release execution requires a Windows host; use distribution_tests.py for archive structure.")
        return
    archive_path = args.release_directory / "ShopController-helper-1.0.0-win-x64.zip"
    with RetryingTemporaryDirectory(prefix="ShopController.PackagedHost.") as temporary:
        root = Path(temporary).resolve()
        host = root / "host"
        host.mkdir()
        prefix = "ShopController-win-x64/host/"
        with zipfile.ZipFile(archive_path) as archive:
            names = safe_names(archive)
            host_names = [name for name in names if name.startswith(prefix) and not name.endswith("/")]
            check(bool(host_names), "Release host payload exists")
            check(sum(archive.getinfo(name).file_size for name in host_names) < 512 * 1024 * 1024, "Bounded release payload")
            for name in host_names:
                path = host.joinpath(*PurePosixPath(name[len(prefix):]).parts)
                check(path.resolve().is_relative_to(host), "Extraction stays within temporary host directory")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(archive.read(name))
        executable = host / "ShopController.Host.exe"
        check(executable.is_file(), "Published Windows apphost exists")
        identity = host / "host-identity.json"
        identifier = "abcdefghijklmnopabcdefghijklmnop"
        origin = f"chrome-extension://{identifier}/"
        body = json.dumps({"action": "get_capabilities"}).encode()
        frame = struct.pack("<I", len(body)) + body
        environment = os.environ.copy()
        environment["DOTNET_BUNDLE_EXTRACT_BASE_DIR"] = str(root / "bundle-extract")

        def invoke(caller):
            return subprocess.run([str(executable), caller], input=frame, capture_output=True,
                                  cwd=host, env=environment, timeout=30,
                                  creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

        missing = invoke(origin)
        check(missing.returncode == 2 and missing.stdout == b"", "Unbound published apphost must fail closed")
        print("PASS published apphost refuses a missing identity without protocol output")
        identity.write_text(json.dumps({"extensionId": identifier}), encoding="utf-8")
        wrong = invoke("chrome-extension://" + "p" * 32 + "/")
        check(wrong.returncode == 2 and wrong.stdout == b"", "Published apphost must refuse an unrelated extension")
        print("PASS published apphost refuses an unrelated extension origin")
        result = invoke(origin)
        check(result.returncode == 0, "Published apphost starts: " + result.stderr.decode(errors="replace"))
        check(len(result.stdout) >= 4 and struct.unpack("<I", result.stdout[:4])[0] == len(result.stdout) - 4,
              "Published host returns exactly one valid native frame")
        reply = json.loads(result.stdout[4:])
        check(reply.get("ok") is True, "Published host capability handshake succeeds")
        check(reply["data"] == {"hostVersion": "1.0.0", "protocolVersion": 1, "platform": "windows", "capabilities": {"pin": True}},
              "Published host capabilities match the Windows release contract")
        check(not (root / "config.json").exists() and not (host / "config.json").exists(), "No fixture shop configuration created")
        print("PASS published self-contained Windows apphost starts and returns release capabilities")
    print("\n3/3 isolated Windows release startup checks passed. No installation, registry or browser action was performed.")


if __name__ == "__main__":
    main()
