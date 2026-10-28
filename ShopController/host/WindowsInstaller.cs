using System.Runtime.Versioning;
using System.Security.Principal;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.Win32;

namespace ShopController.Host;

/// <summary>Explicit, interactive CLI installation; never reachable from native-message actions.</summary>
internal static class WindowsInstaller
{
    internal sealed record Options(string ExtensionId, bool ReplaceIdentity);
    private const string Product = "ShopController";
    private const string HostName = "com.shopcontroller.chrome";
    private const string RegistryPath = @"Software\Google\Chrome\NativeMessagingHosts\com.shopcontroller.chrome";
    private static readonly UTF8Encoding Utf8 = new(false);

    internal static bool IsValidExtensionId(string? id) => id is not null && Regex.IsMatch(id, "\\A[a-p]{32}\\z", RegexOptions.CultureInvariant);

    internal static Options ParseOptions(IReadOnlyList<string> args, bool uninstall)
    {
        if (uninstall && args.Count != 0) throw new ArgumentException("Uninstall takes no target or identity parameters.");
        var id = "";
        var replace = false;
        for (var i = 0; i < args.Count; i++)
        {
            switch (args[i])
            {
                case "--extension-id" when id.Length == 0 && i + 1 < args.Count:
                    id = args[++i];
                    if (!IsValidExtensionId(id)) throw new ArgumentException("Extension ID must be exactly 32 lowercase letters a-p.");
                    break;
                case "--replace-identity" when !replace:
                    replace = true;
                    break;
                default: throw new ArgumentException("Unknown, duplicate, or incomplete installer option.");
            }
        }
        return new Options(id, replace);
    }

    /// <summary>Pure path boundary check used before every installation-directory move.</summary>
    internal static bool IsProductPath(string programsRoot, string candidate)
    {
        try
        {
            if (!Path.IsPathFullyQualified(programsRoot) || !Path.IsPathFullyQualified(candidate) ||
                programsRoot.Any(char.IsControl) || candidate.Any(char.IsControl)) return false;
            var root = Path.GetFullPath(programsRoot).TrimEnd(Path.DirectorySeparatorChar);
            var full = Path.GetFullPath(candidate).TrimEnd(Path.DirectorySeparatorChar);
            if (!string.Equals(Path.GetDirectoryName(full), root, StringComparison.OrdinalIgnoreCase)) return false;
            var name = Path.GetFileName(full);
            return name.Equals(Product, StringComparison.OrdinalIgnoreCase) ||
                new[] { ".stage-", ".previous-", ".failed-" }.Any(s => name.StartsWith(Product + s, StringComparison.OrdinalIgnoreCase));
        }
        catch (Exception ex) when (ex is ArgumentException or NotSupportedException or PathTooLongException) { return false; }
    }

    internal static bool IsOwnedRegistration(string? registered, string expectedManifest) =>
        string.IsNullOrEmpty(registered) || string.Equals(registered, expectedManifest, StringComparison.OrdinalIgnoreCase);

    [SupportedOSPlatform("windows")]
    internal static int Run(string[] arguments, bool uninstall)
    {
        try
        {
            var options = ParseOptions(arguments, uninstall);
            if (!OperatingSystem.IsWindowsVersionAtLeast(10, 0, 22000))
                throw new PlatformNotSupportedException("This release supports Windows 11 x64 in a vendor-supported servicing release.");
            var programs = Path.GetFullPath(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs"));
            var target = Path.Combine(programs, Product);
            AssertSafeProductPath(programs, target);
            var sid = WindowsIdentity.GetCurrent().User?.Value ?? throw new InvalidOperationException("Current Windows user identity is missing.");
            using var mutex = new Mutex(false, "Local\\ShopControllerInstall_" + sid.Replace('-', '_'));
            var locked = false;
            try
            {
                try { locked = mutex.WaitOne(TimeSpan.FromSeconds(30)); }
                catch (AbandonedMutexException) { locked = true; }
                if (!locked) throw new InvalidOperationException("Another installation or uninstall is running. Try again after it finishes.");
                if (uninstall) Uninstall(target);
                else Install(programs, target, options);
            }
            finally { if (locked) mutex.ReleaseMutex(); }
            return 0;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine("Shop Controller setup: " + ex.Message);
            return 1;
        }
    }

    [SupportedOSPlatform("windows")]
    private static void Install(string programs, string target, Options options)
    {
        var source = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, ".."));
        AssertNoRedirect(source);
        if (source.Equals(target, StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("Run Install.cmd from a newly extracted download, not the installed directory.");
        using var metadata = ReadJson(Path.Combine(source, "release-config.json"));
        if (Field(metadata.RootElement, "product") != Product || Field(metadata.RootElement, "runtime") != "win-x64")
            throw new InvalidDataException("This is not a Windows x64 Shop Controller release package.");
        var version = Field(metadata.RootElement, "version");
        if (!Regex.IsMatch(version, "\\A[0-9]+(\\.[0-9]+){1,3}\\z")) throw new InvalidDataException("Release version is invalid.");
        var boundId = Field(metadata.RootElement, "extensionId");
        if (boundId.Length != 0 && !IsValidExtensionId(boundId)) throw new InvalidDataException("Release identity is invalid.");
        if (options.ExtensionId.Length != 0 && boundId.Length != 0 && options.ExtensionId != boundId)
            throw new InvalidDataException("This package is bound to another extension ID.");
        var id = options.ExtensionId.Length != 0 ? options.ExtensionId : boundId;
        if (id.Length == 0)
        {
            Console.Write("Paste the actual Shop Controller ID displayed in chrome://extensions: ");
            id = Console.ReadLine()?.Trim() ?? "";
        }
        if (!IsValidExtensionId(id)) throw new InvalidDataException("The actual extension ID must contain 32 lowercase letters a-p.");
        var sourceHost = Path.Combine(source, "host");
        if (!File.Exists(Path.Combine(sourceHost, "ShopController.Host.exe"))) throw new FileNotFoundException("Extract the entire helper ZIP first.");
        if (Directory.Exists(target))
        {
            EnsureMarker(target);
            using var oldIdentity = ReadJson(Path.Combine(target, "host", "host-identity.json"));
            if (Field(oldIdentity.RootElement, "extensionId") != id && !options.ReplaceIdentity)
                throw new InvalidOperationException("The installed helper uses another ID. Confirm migration, then use --replace-identity.");
        }
        else if (File.Exists(target)) throw new IOException("The installation path is a file; it has been preserved.");
        var manifestPath = Path.Combine(target, HostName + ".json");
        var oldRegistration = ReadRegistration();
        if (!IsOwnedRegistration(oldRegistration, manifestPath))
            throw new InvalidOperationException("Another helper location is registered. Uninstall that registration first: " + oldRegistration);

        Directory.CreateDirectory(programs);
        var suffix = DateTime.Now.ToString("yyyyMMdd-HHmmss") + "-" + Guid.NewGuid().ToString("N")[..6];
        var stage = target + ".stage-" + suffix;
        var backup = target + ".previous-" + suffix;
        var failed = target + ".failed-" + suffix;
        foreach (var path in new[] { stage, backup, failed })
        {
            AssertSafeProductPath(programs, path);
            if (Directory.Exists(path) || File.Exists(path)) throw new IOException("An installation staging path already exists.");
        }
        var movedOld = false;
        var movedNew = false;
        try
        {
            Directory.CreateDirectory(stage);
            CopySafeDirectory(sourceHost, Path.Combine(stage, "host"));
            CopySafeDirectory(Path.Combine(source, "runtime-notices"), Path.Combine(stage, "runtime-notices"));
            foreach (var file in new[] { "release-config.json", "Uninstall.cmd", "README.txt" })
            {
                AssertNoRedirect(Path.Combine(source, file));
                File.Copy(Path.Combine(source, file), Path.Combine(stage, file));
            }
            File.WriteAllText(Path.Combine(stage, ".shopcontroller-install"), Product + " " + version, Utf8);
            WriteJson(Path.Combine(stage, "host", "host-identity.json"), new { extensionId = id });
            WriteJson(Path.Combine(stage, HostName + ".json"), new
            {
                name = HostName, description = "Shop Controller native profile launcher",
                path = Path.Combine(target, "host", "ShopController.Host.exe"), type = "stdio",
                allowed_origins = new[] { "chrome-extension://" + id + "/" }
            });
            if (Directory.Exists(target)) { MoveSafe(programs, target, backup); movedOld = true; }
            MoveSafe(programs, stage, target);
            movedNew = true;
            WriteRegistration(manifestPath);
            Console.WriteLine("Installed 快店快点 helper " + version + " at " + target);
            Console.WriteLine("Allowed extension: " + id);
            Console.WriteLine("Return to the Chrome extension and choose Retry. Chrome profiles and user configuration were not changed.");
            if (movedOld) Console.WriteLine("Previous binaries retained for rollback: " + backup);
        }
        catch
        {
            try
            {
                if (movedNew && Directory.Exists(target)) MoveSafe(programs, target, failed);
                if (movedOld && Directory.Exists(backup)) MoveSafe(programs, backup, target);
                if (movedNew) WriteRegistration(oldRegistration);
            }
            catch (Exception rollback) { Console.Error.WriteLine("Rollback needs attention; backups were preserved: " + rollback.Message); }
            throw;
        }
    }

    [SupportedOSPlatform("windows")]
    private static void Uninstall(string target)
    {
        if (Directory.Exists(target)) EnsureMarker(target);
        var expected = Path.Combine(target, HostName + ".json");
        if (!IsOwnedRegistration(ReadRegistration(), expected)) throw new InvalidOperationException("Registration belongs to another installation and was preserved.");
        WriteRegistration(null);
        // This executable can be running inside target. Never delete/move a running installation.
        Console.WriteLine("Helper registration removed. Configuration, Chrome data, and the extension are unchanged.");
        Console.WriteLine("Installed binaries are retained. After this process closes you may remove this exact folder if no longer needed: " + target);
    }

    private static void EnsureMarker(string target)
    {
        var marker = Path.Combine(target, ".shopcontroller-install");
        AssertNoRedirect(marker);
        if (!File.Exists(marker) || !File.ReadAllText(marker, Utf8).StartsWith(Product + " ", StringComparison.Ordinal))
            throw new InvalidOperationException("Existing directory has no ShopController installation marker; preserved.");
    }

    private static void AssertNoRedirect(string path)
    {
        for (var current = Path.GetFullPath(path); !string.IsNullOrEmpty(current); current = Path.GetDirectoryName(current))
            if ((Directory.Exists(current) || File.Exists(current)) && (File.GetAttributes(current) & FileAttributes.ReparsePoint) != 0)
                throw new IOException("Redirected path is not accepted: " + current);
    }

    private static void AssertSafeProductPath(string programs, string path)
    {
        if (!IsProductPath(programs, path)) throw new IOException("Unexpected installation target.");
        AssertNoRedirect(path);
    }

    private static void MoveSafe(string programs, string from, string to)
    {
        AssertSafeProductPath(programs, from);
        AssertSafeProductPath(programs, to);
        Directory.Move(from, to);
    }

    private static void CopySafeDirectory(string source, string destination)
    {
        AssertNoRedirect(source);
        Directory.CreateDirectory(destination);
        foreach (var entry in Directory.EnumerateFileSystemEntries(source))
        {
            AssertNoRedirect(entry);
            var target = Path.Combine(destination, Path.GetFileName(entry));
            if (Directory.Exists(entry)) CopySafeDirectory(entry, target);
            else File.Copy(entry, target);
        }
    }

    private static JsonDocument ReadJson(string path)
    {
        AssertNoRedirect(path);
        using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
        if (stream.Length > 32768) throw new InvalidDataException("Installer metadata is oversized.");
        return JsonDocument.Parse(stream, new JsonDocumentOptions { MaxDepth = 8 });
    }
    private static string Field(JsonElement item, string key) => item.TryGetProperty(key, out var value) && value.ValueKind == JsonValueKind.String ? value.GetString() ?? "" : "";
    private static void WriteJson(string path, object data) => File.WriteAllText(path, JsonSerializer.Serialize(data, new JsonSerializerOptions { WriteIndented = true }), Utf8);

    [SupportedOSPlatform("windows")]
    private static string? ReadRegistration()
    {
        using var key = Registry.CurrentUser.OpenSubKey(RegistryPath, writable: false);
        var value = key?.GetValue(null, null, RegistryValueOptions.DoNotExpandEnvironmentNames);
        if (value is null) return null;
        if (value is not string text || key!.GetValueKind("") != RegistryValueKind.String)
            throw new InvalidDataException("Existing native-host registration has an unknown value type and was preserved.");
        return text;
    }

    [SupportedOSPlatform("windows")]
    private static void WriteRegistration(string? manifest)
    {
        if (manifest is not null)
        {
            using var key = Registry.CurrentUser.CreateSubKey(RegistryPath);
            key.SetValue("", manifest, RegistryValueKind.String);
        }
        else
        {
            using var key = Registry.CurrentUser.OpenSubKey(RegistryPath, writable: true);
            key?.DeleteValue("", throwOnMissingValue: false);
        }
    }
}
