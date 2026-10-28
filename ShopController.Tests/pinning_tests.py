"""Pinning boundary tests. Never invokes user32, inspects a real window, or starts Chrome."""
from __future__ import annotations

from pathlib import Path
import argparse
import subprocess
import tempfile
from xml.sax.saxutils import escape

from protocol_tests import DOTNET, PROJECT, REPO, TARGET_FRAMEWORK, Host, check, rejected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-build", action="store_true")
    args = parser.parse_args()
    if not args.no_build:
        subprocess.run([str(DOTNET), "build", str(PROJECT), "-c", "Release"], cwd=REPO, check=True)
    with tempfile.TemporaryDirectory(prefix="shop-controller-pin-tests-") as temporary:
        folder = Path(temporary)
        source = REPO / "ShopController" / "host" / "WindowPinning.cs"
        project = folder / "ParseTests.csproj"
        project.write_text(
            '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType>'
            '<TargetFramework>' + TARGET_FRAMEWORK + '</TargetFramework><ImplicitUsings>enable</ImplicitUsings>'
            '<Nullable>enable</Nullable></PropertyGroup><ItemGroup><Compile Include="'
            + escape(str(source), {'"': '&quot;'})
            + '" Link="WindowPinning.cs" /></ItemGroup></Project>',
            encoding="utf-8",
        )
        (folder / "Program.cs").write_text(r'''
using ShopController.Host;

var cases = new (string[] Arguments, nint Expected)[] {
    ([], 0),
    (["--parent-window=1"], 1),
    (["--parent-window=00042"], 42),
    (["--other=5", "--parent-window=12345"], 12345),
    (["--parent-window=0"], 0),
    (["--parent-window="], 0),
    (["--parent-window=-1"], 0),
    (["--parent-window=+1"], 0),
    (["--parent-window= 42"], 0),
    (["--parent-window=42 "], 0),
    (["--parent-window=0x2a"], 0),
    (["--parent-window=４２"], 0),
    (["--parent-window=1", "--parent-window=2"], 0),
    (["--parent-window=18446744073709551615"], 0),
    (["--parent-window=18446744073709551616"], 0),
    (["--parent-window=1\n"], 0),
    (["--parent-window=--help"], 0),
    (["--parent-window=9223372036854775808"], 0),
};
foreach (var (arguments, expected) in cases) {
    var actual = WindowPinning.ParseParentHandle(arguments);
    if (actual != expected) throw new Exception($"Parser case failed: {string.Join(",", arguments)}");
}
Console.WriteLine($"PASS {cases.Length} pure parent-window parser cases; no native API called.");
''', encoding="utf-8")
        subprocess.run([str(DOTNET), "run", "--project", str(project), "-c", "Release"], cwd=REPO, check=True)

        config = folder / "corrupt-config.json"
        config.write_text("not json; must remain untouched", encoding="utf-8")
        before = config.read_bytes()
        with Host(config) as host:
            for action, fields in (
                ("get_launcher_pin", {}),
                ("set_launcher_pin", {"enabled": True}),
                ("set_launcher_pin", {"enabled": False}),
            ):
                reply = host.request(action, **fields)
                rejected(reply)
                check(reply.get("testOnly") is True, f"Test mode must stop before config or native API: {reply}")
            for fields in ({}, {"enabled": "true"}, {"enabled": 1}, {"enabled": None}):
                rejected(host.request("set_launcher_pin", **fields))
            for action, fields in (
                ("get_launcher_pin", {"hwnd": 123}),
                ("set_launcher_pin", {"enabled": True, "hwnd": 123}),
                ("set_launcher_pin", {"enabled": True, "parentWindow": 123}),
                ("set_launcher_pin", {"enabled": True, "processId": 123}),
            ):
                reply = host.request(action, **fields)
                rejected(reply)
                check(reply.get("testOnly") is not True, "Unknown target fields must be rejected before any operation")
            rejected(host.request("get_state"))
        check(config.read_bytes() == before, "Pin requests changed corrupt shop configuration")
        print("PASS 12 pin protocol boundaries and unchanged corrupt configuration; no native API called.")
    print("Pinning tests passed. Real window pinning remains an installation-time acceptance check.")


if __name__ == "__main__":
    main()
