"""Platform policy fixtures; no Chrome process, actual profile, or OS window is accessed."""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

from protocol_tests import DOTNET, REPO, TARGET_FRAMEWORK


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="shop-controller-platform-checks-") as temporary:
        folder = Path(temporary)
        core = REPO / "ShopController.Core" / "ShopController.Core.csproj"
        environment = REPO / "ShopController" / "host" / "HostEnvironment.cs"
        quote = lambda value: escape(str(value), {'"': '&quot;'})
        (folder / "PlatformChecks.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType>'
            f'<TargetFramework>{TARGET_FRAMEWORK}</TargetFramework><ImplicitUsings>enable</ImplicitUsings>'
            '<Nullable>enable</Nullable></PropertyGroup><ItemGroup>'
            f'<ProjectReference Include="{quote(core)}" />'
            f'<Compile Include="{quote(environment)}" Link="HostEnvironment.cs" />'
            '</ItemGroup></Project>', encoding="utf-8")
        (folder / "Program.cs").write_text(r'''
using System.Reflection;
using ShopController.Core;
using ShopController.Host;

var passed = 0;
void Check(bool value, string label) {
    if (!value) throw new Exception(label);
    Console.WriteLine("PASS " + label); passed++;
}
var shape = typeof(ChromeService).GetMethod("IsChromeExecutablePathForPlatform", BindingFlags.NonPublic | BindingFlags.Static)!;
bool Shape(string path, bool mac, bool windows) => (bool)shape.Invoke(null, [path, mac, windows])!;
var shapes = new (string Path, bool Mac, bool Windows, bool Expected)[] {
    ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", true, false, true),
    ("/Users/example/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", true, false, true),
    ("/Volumes/Apps/Google Chrome.app/Contents/MacOS/Google Chrome", true, false, true),
    ("/Applications/Renamed.app/Contents/MacOS/Google Chrome", true, false, true),
    ("/Applications/Google Chrome.app", true, false, false),
    ("/tmp/Google Chrome", true, false, false),
    ("/Applications/Google Chrome/Contents/MacOS/Google Chrome", true, false, false),
    ("/Applications/Google Chrome.app/Contents/MacOS/chrome.exe", true, false, false),
    ("/Applications/Google Chrome.app/Contents/MacOS/google chrome", true, false, false),
    ("/Applications/Google Chrome.app/Contents/Resources/Google Chrome", true, false, false),
    ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome --new-window", true, false, false),
    ("chrome.exe", false, true, true),
    ("CHROME.EXE", false, true, true),
    ("chrome.exe --anything", false, true, false),
    ("Google Chrome", false, true, false),
    ("chrome.exe", false, false, false)
};
foreach (var item in shapes) Check(Shape(item.Path, item.Mac, item.Windows) == item.Expected, "platform executable shape: " + item.Path);
Check(HostEnvironment.Version == "1.0.0" && HostEnvironment.ProtocolVersion == 1, "release protocol metadata");
Check(HostEnvironment.SupportsPin == OperatingSystem.IsWindows(), "pin capability is Windows-only");
Check(HostEnvironment.Platform == (OperatingSystem.IsWindows() ? "windows" : OperatingSystem.IsMacOS() ? "macos" : "unsupported"), "host platform label");

if (OperatingSystem.IsWindows() || OperatingSystem.IsMacOS()) {
    var home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
    var expectedRoot = OperatingSystem.IsMacOS()
        ? Path.Combine(home, "Library", "Application Support", "Google", "Chrome")
        : Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Google", "Chrome", "User Data");
    var expectedConfig = OperatingSystem.IsMacOS()
        ? Path.Combine(home, "Library", "Application Support", "ShopController", "config.json")
        : Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "ShopController", "config.json");
    Check(ChromeService.DefaultUserDataRoot() == expectedRoot, "default Chrome data path matches this OS");
    Check(HostEnvironment.ConfigPath() == expectedConfig, "default product config path matches this OS");

    // Every created file is below the temporary fixture path supplied by the Python wrapper.
    var fixture = Path.GetFullPath(args[0]);
    Directory.CreateDirectory(fixture);
    var executable = OperatingSystem.IsMacOS()
        ? Path.Combine(fixture, "Applications", "Google Chrome.app", "Contents", "MacOS", "Google Chrome")
        : Path.Combine(fixture, "chrome.exe");
    Directory.CreateDirectory(Path.GetDirectoryName(executable)!);
    File.WriteAllText(executable, "inert test file, never executed");
    if (OperatingSystem.IsMacOS()) File.SetUnixFileMode(executable, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
    Check(ChromeService.ValidateChromeExecutable(executable) == executable, "existing fixture executable validates");
    var root = Path.Combine(fixture, "资料 空间");
    Directory.CreateDirectory(Path.Combine(root, "Profile 7"));
    const string url = "https://shop.jd.com/?x=a%20b#订单";
    var start = ChromeService.BuildStartInfo(executable, root, "Profile 7", url);
    Check(start.FileName == executable && !start.UseShellExecute &&
        start.ArgumentList.SequenceEqual(new[] { "--user-data-dir=" + root, "--profile-directory=Profile 7", url }), "OS fixture launch arguments stay separate and exact");
    if (OperatingSystem.IsMacOS()) {
        File.SetUnixFileMode(executable, UnixFileMode.UserRead | UnixFileMode.UserWrite);
        var rejected = false;
        try { ChromeService.ValidateChromeExecutable(executable); } catch (ArgumentException) { rejected = true; }
        Check(rejected, "Mac fixture without execute bit is rejected");
    }
    var configPath = Path.Combine(fixture, "config", "config.json");
    Directory.CreateDirectory(Path.GetDirectoryName(configPath)!);
    var parentMode = !OperatingSystem.IsWindows() ? File.GetUnixFileMode(Path.GetDirectoryName(configPath)!) : (UnixFileMode?)null;
    var store = new ConfigStore(configPath);
    store.Save(new AppConfig());
    store.Save(new AppConfig());
    Check(store.Load().Version == 1 && File.Exists(configPath + ".bak"), "atomic config and previous good backup remain valid");
    if (!OperatingSystem.IsWindows()) {
        var expectedMode = UnixFileMode.UserRead | UnixFileMode.UserWrite;
        Check(File.GetUnixFileMode(configPath) == expectedMode, "new config is owner read/write only");
        Check(File.GetUnixFileMode(configPath + ".bak") == expectedMode, "new config backup retains owner-only permissions");
        Check(File.GetUnixFileMode(Path.GetDirectoryName(configPath)!) == parentMode, "existing parent permissions are unchanged");
    }
}
Console.WriteLine($"{passed} platform checks passed. No browser or real profile was accessed.");
''', encoding="utf-8")
        subprocess.run([str(DOTNET), "run", "--project", str(folder / "PlatformChecks.csproj"),
                        "-c", "Release", "--", str(folder / "fixtures")], cwd=REPO, check=True)


if __name__ == "__main__":
    main()
