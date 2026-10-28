"""Native-messaging integration tests. Never registers a host or starts Chrome.

Run from the repository root:
  python ShopController.Tests/protocol_tests.py
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
import queue
import struct
import subprocess
import sys
import tempfile
import threading
import uuid
import xml.etree.ElementTree as ET

# Do not create SDK development certificates or send SDK usage telemetry in tests.
os.environ.setdefault("DOTNET_CLI_TELEMETRY_OPTOUT", "1")
os.environ.setdefault("DOTNET_GENERATE_ASPNET_CERTIFICATE", "false")
os.environ.setdefault("DOTNET_NOLOGO", "1")


REPO = Path(__file__).resolve().parents[1]
PROJECT = REPO / "ShopController" / "host" / "ShopController.Host.csproj"
TARGET_FRAMEWORK = ET.parse(PROJECT).findtext(".//TargetFramework")
check_target = TARGET_FRAMEWORK and TARGET_FRAMEWORK.startswith("net") and "/" not in TARGET_FRAMEWORK and "\\" not in TARGET_FRAMEWORK
if not check_target:
    raise RuntimeError("Host project has no valid TargetFramework")
_dotnet_name = "dotnet.exe" if os.name == "nt" else "dotnet"
_bundled_candidates = [REPO / ".tools" / folder / _dotnet_name for folder in ("dotnet10", "dotnet")]
DOTNET = next((candidate for candidate in _bundled_candidates if candidate.exists()), Path(shutil.which("dotnet") or "dotnet"))
DLL = PROJECT.parent / "bin" / "Release" / TARGET_FRAMEWORK / "ShopController.Host.dll"


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def ok(reply: dict) -> dict:
    check(reply.get("ok") is True, f"Expected success, received {reply!r}")
    return reply["data"]


def rejected(reply: dict) -> None:
    check(reply.get("ok") is False, f"Expected rejection, received {reply!r}")
    check(bool(reply.get("error")), "A rejection must explain the problem")


def read_exact(stream, count: int) -> bytes:
    result = bytearray()
    while len(result) < count:
        data = stream.read(count - len(result))
        if not data:
            raise EOFError("Native host closed the response pipe")
        result.extend(data)
    return bytes(result)


class Host:
    def __init__(self, config: Path):
        self.process = subprocess.Popen(
            [str(DOTNET), str(DLL), "--protocol-test", str(config)],
            cwd=REPO,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self.responses: queue.Queue = queue.Queue()
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self) -> None:
        try:
            while True:
                length = struct.unpack("<I", read_exact(self.process.stdout, 4))[0]
                check(0 < length <= 1_000_000, "Host returned invalid frame length")
                body = read_exact(self.process.stdout, length)
                self.responses.put(json.loads(body.decode("utf-8")))
        except BaseException as error:
            self.responses.put(error)

    def raw(self, body: bytes) -> dict:
        self.process.stdin.write(struct.pack("<I", len(body)) + body)
        self.process.stdin.flush()
        try:
            reply = self.responses.get(timeout=12)
        except queue.Empty as error:
            raise AssertionError("Native host response timed out") from error
        if isinstance(reply, BaseException):
            raise reply
        return reply

    def request(self, action: str, **fields) -> dict:
        return self.raw(json.dumps({"action": action, **fields}, ensure_ascii=False).encode("utf-8"))

    def close(self) -> None:
        if self.process.poll() is None:
            self.process.stdin.close()
            try:
                self.process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=8)
                raise AssertionError("Native host failed to exit after stdin EOF")
        stderr = self.process.stderr.read().decode("utf-8", errors="replace")
        check(self.process.returncode == 0, f"Host exited {self.process.returncode}: {stderr}")

    def __enter__(self):
        return self

    def __exit__(self, error_type, error, traceback):
        if error_type is not None:
            self.process.kill()
            self.process.wait(timeout=8)
        else:
            self.close()


def fixture(parent: Path) -> tuple[Path, Path]:
    executable_path = Path("Google Chrome.app/Contents/MacOS/Google Chrome") if sys.platform == "darwin" else Path("chrome.exe")
    exe = parent / "Chrome test 中文" / executable_path
    exe.parent.mkdir(parents=True)
    exe.write_text("TEST-ONLY TEXT PLACEHOLDER. NEVER EXECUTE.", encoding="utf-8")
    if sys.platform == "darwin":
        exe.chmod(0o700)  # Validation only; the protocol test mode never executes this fixture.
    data = parent / "User Data 中文"
    for name in ("Default", "Profile 1", "Profile 2"):
        profile = data / name
        profile.mkdir(parents=True)
        (profile / "sentinel.txt").write_text("Do not delete browser data", encoding="utf-8")
    (data / "Local State").write_text(json.dumps({
        "profile": {"info_cache": {
            "Default": {"name": "测试资料一"},
            "Profile 1": {"name": "测试资料二"},
            "Profile 2": {"name": "测试资料三"},
        }}
    }, ensure_ascii=False), encoding="utf-8")
    return exe, data


def shop(name: str, platform: str, alias: str, identifier: str | None = None) -> dict:
    return {
        "id": str(uuid.uuid4()) if identifier is None else identifier,
        "name": name,
        "platform": platform,
        "accountAlias": alias,
        "profileDirectory": "",
        "homeUrl": "https://example.com/merchant?name=a%20b&signed=%2B%2F#订单",
        "notes": "Temporary native protocol fixture",
        "lastOpenedAt": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-build", action="store_true")
    args = parser.parse_args()
    if not args.no_build:
        subprocess.run([str(DOTNET), "build", str(PROJECT), "-c", "Release"], cwd=REPO, check=True)
    check(DLL.exists(), f"Missing host build: {DLL}")

    passed: list[str] = []

    def passed_step(name: str) -> None:
        passed.append(name)
        print(f"PASS  {name}", flush=True)

    with tempfile.TemporaryDirectory(prefix="ShopController.Protocol.") as folder:
        # Windows CI TEMP can use an 8.3 alias. Canonicalize the existing fixture
        # parent before seeding paths so Python and .NET compare the same spelling.
        root = Path(folder).resolve(strict=True)
        initial_exe, initial_data = fixture(root / "initial")
        active_exe, active_data = fixture(root / "active")
        config = root / "config.json"
        # Preseed fake paths: even get_state cannot fall back to real Chrome metadata.
        config.write_text(json.dumps({
            "version": 1, "chromeExecutable": str(initial_exe),
            "userDataRoot": str(initial_data), "shops": [],
        }), encoding="utf-8")

        with Host(config) as host:
            state = ok(host.request("get_state"))
            check(state["testMode"] is True, "Protocol tests must be in no-launch mode")
            check(len(state["profiles"]) == 3 and state["config"]["shops"] == [], "Initial fixture state")
            initial_revision = state["revision"]
            passed_step("get_state returns fixture profiles and a revision")

            state = ok(host.request("save_settings", revision=initial_revision,
                chromeExecutable=str(active_exe), userDataRoot=str(active_data)))
            check(state["userDataRoot"] == str(active_data), "Settings must select the fixture data root")
            check(state["revision"] != initial_revision, "Settings change must update revision")
            passed_step("save_settings persists explicit fake Chrome paths")

            rejected(host.request("save_settings", revision=initial_revision,
                chromeExecutable=str(initial_exe), userDataRoot=str(initial_data)))
            check(ok(host.request("get_state"))["userDataRoot"] == str(active_data), "Stale save must not overwrite")
            passed_step("stale settings revision is rejected without overwrite")

            first = shop("京东店铺 A", "JD", "jd-account", "")
            state = ok(host.request("save_shop", revision=state["revision"], shop=first))
            first = state["config"]["shops"][0]
            check(str(uuid.UUID(first["id"])) == first["id"], "Generated ID must be D-format GUID")
            after_first_revision = state["revision"]
            second = shop("淘宝店铺 A", "Taobao", "tb-account")
            state = ok(host.request("save_shop", revision=state["revision"], shop=second))
            check(len(state["config"]["shops"]) == 2, "Two shops saved")
            passed_step("save_shop handles generated GUID and two different platforms")

            rejected(host.request("save_shop", revision=after_first_revision, shop=shop("Stale", "JD", "stale")))
            check(len(ok(host.request("get_state"))["config"]["shops"]) == 2, "Stale shop save must not add a record")
            passed_step("stale shop revision is rejected without adding a record")

            allowed_profiles = ["Profile 1", "Profile 2"]
            plan = ok(host.request("plan_assignments", profileDirectories=allowed_profiles))
            check(plan["plan"]["canApply"] and plan["plan"]["requiredProfiles"] == 1, "Different platforms should share one fixture profile")
            check(len(plan["plan"]["assignments"]) == 2, "Plan contains both shops")
            check(bool(plan.get("planToken")), "Preview must return a token")
            check(all(item["profileDirectory"] in allowed_profiles for item in plan["plan"]["assignments"]), "Unselected main profile must not be used")
            rejected(host.request("apply_plan", revision=plan["revision"], profileDirectories=allowed_profiles))
            rejected(host.request("apply_plan", revision=plan["revision"], planToken=plan["planToken"], profileDirectories=["Default"]))
            local_state = active_data / "Local State"
            original_metadata = local_state.read_text(encoding="utf-8")
            changed_metadata = json.loads(original_metadata)
            changed_metadata["profile"]["info_cache"]["Profile 1"]["name"] = "Changed after preview"
            local_state.write_text(json.dumps(changed_metadata), encoding="utf-8")
            rejected(host.request("apply_plan", revision=plan["revision"], planToken=plan["planToken"], profileDirectories=allowed_profiles))
            local_state.write_text(original_metadata, encoding="utf-8")
            check(ok(host.request("get_state"))["revision"] == state["revision"], "Rejected plans must not save")
            passed_step("plan token binds selected profiles and rejects stale metadata or changed pool")

            empty_plan = ok(host.request("plan_assignments", profileDirectories=[]))
            check(empty_plan["plan"]["canApply"] is False, "An empty profile pool has insufficient capacity")
            rejected(host.request("apply_plan", revision=empty_plan["revision"], planToken=empty_plan["planToken"], profileDirectories=[]))
            state = ok(host.request("apply_plan", revision=plan["revision"], planToken=plan["planToken"], profileDirectories=allowed_profiles))
            assigned = {entry["profileDirectory"] for entry in state["config"]["shops"]}
            check(len(assigned) == 1 and assigned.issubset(allowed_profiles), "Both platforms must receive the same selected profile")
            passed_step("plan_assignments and apply_plan compress independent platforms")

            rejected(host.request("open_shop", id=first["id"]))
            rejected(host.request("open_shop", id=first["id"], revision=after_first_revision))
            passed_step("open_shop requires a current revision before using a shop binding")
            for entry in state["config"]["shops"]:
                opened = ok(host.request("open_shop", id=entry["id"], revision=state["revision"]))
                check(opened["testOnly"] is True and opened["opened"] is False, "open_shop must not launch in protocol tests")
                expected_arguments = [f"--user-data-dir={active_data}",
                    f"--profile-directory={entry['profileDirectory']}", entry["homeUrl"]]
                check(opened["arguments"] == expected_arguments,
                    f"Exact shell-free argument array differs: expected={expected_arguments!r}; actual={opened['arguments']!r}")
            passed_step("open_shop only builds exact per-profile launch arguments")

            for request in (b'{"action":', b'[]', b'{"action":"unknown-operation"}', b'{}'):
                rejected(host.raw(request))
            check(ok(host.request("get_state"))["revision"] == state["revision"], "Malformed requests must leave state intact")
            passed_step("malformed JSON, non-object, unknown action, and missing action are rejected")

            for action in ("--install-user", "--uninstall-user", "install_user", "uninstall_user"):
                rejected(host.request(action))
            check(ok(host.request("get_state"))["revision"] == state["revision"], "CLI names must not mutate configuration through Native Messaging")
            passed_step("installer command names are never exposed as Native Messaging actions")

            rejected(host.request("delete_shop", revision=after_first_revision, id=first["id"]))
            state = ok(host.request("delete_shop", revision=state["revision"], id=first["id"]))
            check(len(state["config"]["shops"]) == 1, "Only entry deleted")
            for directory in ("Default", "Profile 1", "Profile 2"):
                check((active_data / directory / "sentinel.txt").read_text(encoding="utf-8") == "Do not delete browser data", "Deleting an entry must not remove browser files")
            passed_step("delete_shop removes only configuration and preserves every profile")
            saved_revision = state["revision"]

        with Host(config) as restarted:
            state = ok(restarted.request("get_state"))
            check(state["revision"] == saved_revision, "Revision persists across host restart")
            check(len(state["config"]["shops"]) == 1 and state["config"]["shops"][0]["id"] == second["id"], "Shop persists across restart")
            check(state["chromeExecutable"] == str(active_exe), "Settings persist across restart")
        check(Path(str(config) + ".bak").exists(), "Mutations should retain a configuration backup")
        passed_step("configuration, bindings, settings, and backup survive restart")

        large_config = root / "large-config.json"
        large_shops = [shop(f"Large fixture {index}", "JD", "same-account") for index in range(120)]
        for entry in large_shops:
            entry["notes"] = "测" * 2000
        large_text = json.dumps({"version": 1, "chromeExecutable": str(active_exe),
            "userDataRoot": str(active_data), "shops": large_shops}, ensure_ascii=False)
        large_config.write_text(large_text, encoding="utf-8")
        with Host(large_config) as large_host:
            rejected(large_host.request("get_state"))
            large_plan = ok(large_host.request("plan_assignments", profileDirectories=["Profile 1"]))
            rejected(large_host.request("apply_plan", revision=large_plan["revision"],
                planToken=large_plan["planToken"], profileDirectories=["Profile 1"]))
            check(large_config.read_text(encoding="utf-8") == large_text, "Response size guard must prevent oversized mutation from being saved")
            ok(large_host.request("plan_assignments", profileDirectories=["Profile 1"]))
        passed_step("oversized state returns structured errors and oversized saves preserve the original")

        process = subprocess.run([str(DOTNET), str(DLL)], cwd=REPO, input=b"", capture_output=True, timeout=12,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        check(process.returncode == 2, "Missing extension origin must exit 2")
        check(process.stdout == b"", "No-origin rejection must not write nonprotocol text to stdout")
        passed_step("normal protocol launch without extension origin exits 2")

        process = subprocess.run([str(DOTNET), str(DLL), "--protocol-test", str(config)], cwd=REPO,
            input=struct.pack("<I", 0), capture_output=True, timeout=12,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        check(process.returncode == 1, "Zero-length frame must terminate with an error")
        check(process.stdout == b"", "Invalid frame must not corrupt stdout framing")
        passed_step("invalid zero-length frame exits cleanly with an error")

    print(f"\n{len(passed)}/{len(passed)} native protocol integration checks passed.")
    print("No native host was registered; no Chrome process, real profile, Cookie, or network was accessed.")


if __name__ == "__main__":
    main()
