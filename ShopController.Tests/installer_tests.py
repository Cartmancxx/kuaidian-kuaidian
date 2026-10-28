"""Pure Windows installer option/path/identity policy checks; never invokes Run()."""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

from protocol_tests import DOTNET, REPO, TARGET_FRAMEWORK, check


def main():
    installer = REPO / "ShopController/host/WindowsInstaller.cs"
    entry = (REPO / "ShopController/host/Program.cs").read_text(encoding="utf-8")
    worker = (REPO / "ShopController/extension/background.js").read_text(encoding="utf-8")
    check("WindowsInstaller" not in entry.split("internal sealed class Dispatcher", 1)[1], "Installer is absent from native request dispatcher")
    for token in ("--install-user", "--uninstall-user", "install_user", "uninstall_user"):
        check(token not in worker, "Extension worker never exposes installation actions")
    for name, expected in [("Install.cmd", "--install-user"), ("Uninstall.cmd", "--uninstall-user")]:
        command = (REPO / "ShopController/scripts/release/windows" / name).read_text(encoding="utf-8-sig")
        check("ShopController.Host.exe" in command and expected in command, "User command directly invokes the explicit local helper CLI")
        check("powershell" not in command.lower() and "executionpolicy" not in command.lower(), "Default launcher does not modify PowerShell security settings")
    print("PASS installer entry is not a native action and user wrappers call the local CLI directly")

    with tempfile.TemporaryDirectory(prefix="ShopController.InstallerPolicy.") as temporary:
        root = Path(temporary)
        quote = escape(str(installer), {'"': '&quot;'})
        (root / "InstallerChecks.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType>'
            f'<TargetFramework>{TARGET_FRAMEWORK}</TargetFramework><ImplicitUsings>enable</ImplicitUsings>'
            '<Nullable>enable</Nullable><TreatWarningsAsErrors>true</TreatWarningsAsErrors>'
            '</PropertyGroup><ItemGroup>'
            f'<Compile Include="{quote}" Link="WindowsInstaller.cs" />'
            '</ItemGroup></Project>', encoding="utf-8")
        (root / "Program.cs").write_text(r'''
using ShopController.Host;

var passed = 0;
void Check(bool result, string label) {
    if (!result) throw new Exception(label);
    Console.WriteLine("PASS " + label); passed++;
}
void Reject(string[] args, bool uninstall, string label) {
    var rejected = false;
    try { WindowsInstaller.ParseOptions(args, uninstall); }
    catch (ArgumentException) { rejected = true; }
    Check(rejected, label);
}
const string id = "abcdefghijklmnopabcdefghijklmnop";
Check(WindowsInstaller.IsValidExtensionId(id), "valid extension identity");
Check(WindowsInstaller.IsValidExtensionId(new string('p', 32)), "valid upper alphabet boundary");
foreach (var bad in new string?[] { null, "", new string('a', 31), new string('a', 33), new string('A', 32), new string('q', 32), id + "\n", " " + id, id + " ", "chrome-extension://" + id + "/" })
    Check(!WindowsInstaller.IsValidExtensionId(bad), "invalid identity rejected: " + (bad is null ? "null" : bad.Replace("\n", "\\n")));

var options = WindowsInstaller.ParseOptions([], false);
Check(options.ExtensionId == "" && !options.ReplaceIdentity, "interactive install options can omit ID");
options = WindowsInstaller.ParseOptions(["--extension-id", id], false);
Check(options.ExtensionId == id && !options.ReplaceIdentity, "explicit valid ID is preserved exactly");
options = WindowsInstaller.ParseOptions(["--replace-identity", "--extension-id", id], false);
Check(options.ExtensionId == id && options.ReplaceIdentity, "explicit identity migration flag is preserved");
options = WindowsInstaller.ParseOptions(["--extension-id", id, "--replace-identity"], false);
Check(options.ExtensionId == id && options.ReplaceIdentity, "option order does not change identity binding");
options = WindowsInstaller.ParseOptions([], true);
Check(options.ExtensionId == "" && !options.ReplaceIdentity, "uninstall has no implicit override");
foreach (var invalid in new[] {
    new[] { "--extension-id" }, new[] { "--extension-id", "" },
    new[] { "--extension-id", id, "--extension-id", id },
    new[] { "--replace-identity", "--replace-identity" },
    new[] { "--Extension-id", id }, new[] { "--target", "C:\\unrelated" },
    new[] { "--extension-id", id, "extra" }, new[] { "--extension-id", id + "\n" }
}) Reject(invalid, false, "unsafe or ambiguous install options rejected");
Reject(["--extension-id", id], true, "uninstall rejects identity overrides");
Reject(["--replace-identity"], true, "uninstall rejects migration flags");

// Strings only: no product directory is created and no file/registry operation is invoked.
var programs = Path.Combine(Path.GetTempPath(), "ShopController.InstallerMatrix", "Programs");
foreach (var name in new[] { "ShopController", "shopcontroller", "ShopController.stage-fixture", "ShopController.previous-fixture", "ShopController.failed-fixture" })
    Check(WindowsInstaller.IsProductPath(programs, Path.Combine(programs, name)), "product-boundary accepts expected direct child: " + name);
foreach (var candidate in new[] {
    programs, Path.Combine(programs, "OtherProduct"), Path.Combine(programs, "ShopControllerEvil"),
    Path.Combine(programs, "ShopController", "host"), Path.Combine(programs, "Other", "ShopController"),
    Path.Combine(programs, "..", "ShopController"), "relative/ShopController",
    Path.Combine(programs, "ShopController\n"), Path.Combine(programs, "ShopController.backup")
}) Check(!WindowsInstaller.IsProductPath(programs, candidate), "product-boundary rejects unrelated destination");
Check(!WindowsInstaller.IsProductPath("relative/Programs", Path.Combine(programs, "ShopController")), "relative Programs root is rejected");

var manifest = Path.Combine(programs, "ShopController", "com.shopcontroller.chrome.json");
Check(WindowsInstaller.IsOwnedRegistration(null, manifest), "missing registration may be installed");
Check(WindowsInstaller.IsOwnedRegistration("", manifest), "empty registration may be installed");
Check(WindowsInstaller.IsOwnedRegistration(manifest, manifest), "exact existing registration belongs to product");
Check(WindowsInstaller.IsOwnedRegistration(manifest.ToUpperInvariant(), manifest), "Windows registry path match is case insensitive");
Check(!WindowsInstaller.IsOwnedRegistration(manifest + ".other", manifest), "unrelated registration is preserved");
Check(!WindowsInstaller.IsOwnedRegistration("%LOCALAPPDATA%/ShopController/manifest.json", manifest), "an alternate or unexpanded path is not assumed to be owned");
Console.WriteLine($"{passed} pure installer policy checks passed. Run(), filesystem changes and registry APIs were not invoked.");
''', encoding="utf-8")
        subprocess.run([str(DOTNET), "run", "--project", str(root / "InstallerChecks.csproj"), "-c", "Release"], check=True, cwd=root)


if __name__ == "__main__":
    main()
