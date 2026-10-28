using System.Diagnostics;
using System.Security;
using System.Text.Json;
using Microsoft.Win32;

namespace ShopController.Core;

/// <summary>
/// Reads Chrome's non-secret profile names and opens a URL in an existing profile.
/// This service never reads Cookies, Login Data, Preferences, or browser lock files.
/// </summary>
public static class ChromeService
{
    private const string AppPathsKey = @"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe";
    private const long MaximumLocalStateBytes = 32 * 1024 * 1024;

    /// <summary>Looks at registered and standard installation paths; does not start Chrome.</summary>
    public static string? DetectChromeExecutable()
    {
        if (OperatingSystem.IsMacOS())
        {
            foreach (var applications in new[]
            {
                "/Applications",
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Applications")
            })
            {
                var candidate = Path.Combine(applications, "Google Chrome.app", "Contents", "MacOS", "Google Chrome");
                if (IsExistingChromeExecutable(candidate)) return Path.GetFullPath(candidate);
            }
            return null;
        }
        if (!OperatingSystem.IsWindows()) return null;
        if (OperatingSystem.IsWindows())
        {
            foreach (var hive in new[] { RegistryHive.CurrentUser, RegistryHive.LocalMachine })
            {
                foreach (var view in new[] { RegistryView.Registry64, RegistryView.Registry32 })
                {
                    try
                    {
                        using var baseKey = RegistryKey.OpenBaseKey(hive, view);
                        using var key = baseKey.OpenSubKey(AppPathsKey, writable: false);
                        if (key?.GetValue(null) is string registered)
                        {
                            // App Paths stores a file path, not an executable plus arguments.
                            var candidate = registered.Trim().Trim('"');
                            if (IsExistingChromeExecutable(candidate))
                                return Path.GetFullPath(candidate);
                        }
                    }
                    catch (Exception ex) when (ex is UnauthorizedAccessException or SecurityException or IOException)
                    {
                        // A restricted registry view should not hide a standard installation.
                    }
                }
            }
        }

        foreach (var folder in new[]
        {
            Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),
            Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86),
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData)
        })
        {
            if (string.IsNullOrWhiteSpace(folder))
                continue;

            var candidate = Path.Combine(folder, "Google", "Chrome", "Application", "chrome.exe");
            if (IsExistingChromeExecutable(candidate))
                return Path.GetFullPath(candidate);
        }

        return null;
    }

    public static string DefaultUserDataRoot()
    {
        if (OperatingSystem.IsMacOS()) return Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Library", "Application Support", "Google", "Chrome");
        if (OperatingSystem.IsWindows()) return Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Google", "Chrome", "User Data");
        throw new PlatformNotSupportedException("此版本支持 Windows 和 macOS 的 Google Chrome。");
    }

    /// <summary>Validates the native Chrome binary for the current OS without executing it.</summary>
    public static string ValidateChromeExecutable(string executable)
    {
        var path = NormalizeAbsolutePath(executable, nameof(executable));
        if (!IsChromeExecutablePathForPlatform(path, OperatingSystem.IsMacOS(), OperatingSystem.IsWindows()))
            throw new ArgumentException(OperatingSystem.IsMacOS()
                ? "请选择 Google Chrome.app 内 Contents/MacOS/Google Chrome 程序的完整路径。"
                : "浏览器程序必须为 chrome.exe。", nameof(executable));
        if (!File.Exists(path)) throw new FileNotFoundException("未找到 Chrome 程序，请重新选择现有程序。", path);
        if (OperatingSystem.IsMacOS() && (File.GetUnixFileMode(path) &
            (UnixFileMode.UserExecute | UnixFileMode.GroupExecute | UnixFileMode.OtherExecute)) == 0)
            throw new ArgumentException("Chrome 程序没有可执行权限，请确认选择了已正常安装的应用。", nameof(executable));
        return path;
    }

    // The platform-specific name check is intentionally separate for fixture tests;
    // this does not establish publisher trust or replace the OS signature checks.
    internal static bool IsChromeExecutablePathForPlatform(string path, bool macOS, bool windows)
    {
        if (windows) return Path.GetFileName(path).Equals("chrome.exe", StringComparison.OrdinalIgnoreCase);
        if (!macOS) return false;
        var normalized = path.Replace('\\', '/');
        var segments = normalized.Split('/', StringSplitOptions.RemoveEmptyEntries);
        return segments.Length >= 4 && segments[^1] == "Google Chrome" && segments[^2] == "MacOS" &&
            segments[^3] == "Contents" && segments[^4].EndsWith(".app", StringComparison.Ordinal);
    }

    /// <summary>
    /// Reads only profile.info_cache keys and their name fields from Local State.
    /// Missing data returns an empty list. Invalid JSON is reported, not mistaken for no profiles.
    /// </summary>
    public static IReadOnlyList<ProfileInfo> DiscoverProfiles(string userDataRoot)
    {
        var root = NormalizeAbsolutePath(userDataRoot, nameof(userDataRoot));
        if (!Directory.Exists(root))
            return Array.Empty<ProfileInfo>();

        var localState = Path.Combine(root, "Local State");
        try
        {
            using var stream = new FileStream(localState, FileMode.Open, FileAccess.Read,
                FileShare.ReadWrite | FileShare.Delete);
            if (stream.Length > MaximumLocalStateBytes)
                throw new InvalidDataException("Chrome 的 Local State 文件超过资料列表读取上限（32 MB）。");

            using var document = JsonDocument.Parse(stream, new JsonDocumentOptions { MaxDepth = 64 });
            var element = document.RootElement;
            if (element.ValueKind != JsonValueKind.Object)
                throw new InvalidDataException("Chrome 的 Local State 顶层应为 JSON 对象。");

            if (!element.TryGetProperty("profile", out var profile))
                return Array.Empty<ProfileInfo>();
            if (profile.ValueKind != JsonValueKind.Object)
                throw new InvalidDataException("Chrome 的 Local State 中 profile 字段格式无效。");
            if (!profile.TryGetProperty("info_cache", out var cache))
                return Array.Empty<ProfileInfo>();
            if (cache.ValueKind != JsonValueKind.Object)
                throw new InvalidDataException("Chrome 的 Local State 中 profile.info_cache 字段格式无效。");

            var profiles = new Dictionary<string, ProfileInfo>(StringComparer.OrdinalIgnoreCase);
            foreach (var entry in cache.EnumerateObject())
            {
                if (!IsSafeProfileDirectoryName(entry.Name) || !IsExistingProfileDirectory(root, entry.Name))
                    continue;

                var displayName = entry.Name;
                if (entry.Value.ValueKind == JsonValueKind.Object &&
                    entry.Value.TryGetProperty("name", out var name) && name.ValueKind == JsonValueKind.String)
                {
                    var configuredName = name.GetString();
                    if (!string.IsNullOrWhiteSpace(configuredName))
                        displayName = configuredName;
                }

                profiles[entry.Name] = new ProfileInfo(entry.Name, displayName);
            }

            return profiles.Values
                .OrderBy(p => p.DirectoryName.Equals("Default", StringComparison.OrdinalIgnoreCase) ? 0 : 1)
                .ThenBy(p => p.DirectoryName, StringComparer.OrdinalIgnoreCase)
                .ToArray();
        }
        catch (FileNotFoundException)
        {
            return Array.Empty<ProfileInfo>();
        }
        catch (DirectoryNotFoundException)
        {
            return Array.Empty<ProfileInfo>();
        }
        catch (JsonException ex)
        {
            throw new InvalidDataException(
                "Chrome 的 Local State 不是有效 JSON，资料列表尚未读取成功。请稍后刷新；原文件未被修改。", ex);
        }
        catch (UnauthorizedAccessException ex)
        {
            throw new IOException("没有读取 Chrome 资料列表 Local State 的权限；原文件未被修改。", ex);
        }
    }

    /// <summary>
    /// Builds independently testable, shell-free launch arguments. This does not start a process.
    /// An existing test file named chrome.exe is sufficient for argument-construction tests.
    /// </summary>
    public static ProcessStartInfo BuildStartInfo(
        string executable, string userDataRoot, string profileDirectory, string url)
    {
        var chromePath = ValidateChromeExecutable(executable);

        var root = NormalizeAbsolutePath(userDataRoot, nameof(userDataRoot));
        if (!Directory.Exists(root))
            throw new DirectoryNotFoundException("Chrome 用户数据目录不存在，请重新选择现有目录。");
        if (!IsSafeProfileDirectoryName(profileDirectory))
            throw new ArgumentException("Chrome 资料目录名称无效，请选择现有资料。", nameof(profileDirectory));
        if (!IsExistingProfileDirectory(root, profileDirectory))
            throw new DirectoryNotFoundException("选定的 Chrome 资料目录不存在，或不是安全的直接子目录。请刷新资料列表。");

        var targetUrl = ValidateHttpUrl(url);
        var info = new ProcessStartInfo
        {
            FileName = chromePath,
            UseShellExecute = false,
            WorkingDirectory = Path.GetDirectoryName(chromePath)!
        };
        info.ArgumentList.Add($"--user-data-dir={root}");
        info.ArgumentList.Add($"--profile-directory={profileDirectory}");
        info.ArgumentList.Add(targetUrl);
        return info;
    }

    /// <summary>
    /// Hands the URL to Chrome. Success means the launch request was sent, not that a user is
    /// signed in or that a particular existing tab was activated. Chrome handles its own profiles.
    /// </summary>
    public static void Open(string executable, string userDataRoot, string profileDirectory, string url)
    {
        var startInfo = BuildStartInfo(executable, userDataRoot, profileDirectory, url);
        using var process = Process.Start(startInfo);
        if (process is null)
            throw new InvalidOperationException("Chrome 未接受启动请求，请检查程序路径后重试。");
    }

    private static string ValidateHttpUrl(string url)
    {
        if (string.IsNullOrWhiteSpace(url) || url != url.Trim() || url.Any(char.IsControl) || url.Contains('\\') ||
            !Uri.TryCreate(url, UriKind.Absolute, out var uri) ||
            (uri.Scheme != Uri.UriSchemeHttps && uri.Scheme != Uri.UriSchemeHttp) ||
            string.IsNullOrWhiteSpace(uri.Host) || !string.IsNullOrEmpty(uri.UserInfo))
        {
            throw new ArgumentException("后台地址须为完整的 HTTP 或 HTTPS 网址，且不含账号密码、控制字符或反斜线。", nameof(url));
        }

        if (Uri.UnescapeDataString(url).Any(char.IsControl))
            throw new ArgumentException("后台地址含有编码后的控制字符，请重新复制平台入口。", nameof(url));

        // Keep signed URLs and already escaped platform deep links byte-for-byte intact.
        // ArgumentList passes this as one argument, so URI reformatting is unnecessary.
        return url;
    }

    private static string NormalizeAbsolutePath(string path, string parameterName)
    {
        if (string.IsNullOrWhiteSpace(path) || path.Any(char.IsControl) || path.Contains('"') ||
            !Path.IsPathFullyQualified(path))
        {
            throw new ArgumentException("请提供完整的本地绝对路径。", parameterName);
        }

        return Path.GetFullPath(path);
    }

    private static bool IsExistingChromeExecutable(string path)
    {
        try
        {
            _ = ValidateChromeExecutable(path);
            return true;
        }
        catch (Exception ex) when (ex is ArgumentException or NotSupportedException or IOException or UnauthorizedAccessException or SecurityException)
        {
            return false;
        }
    }

    private static bool IsSafeProfileDirectoryName(string? name)
    {
        if (string.IsNullOrWhiteSpace(name) || name.Length > 128 || name != name.Trim() ||
            name.StartsWith('-') || name.EndsWith('.') || name.Contains("..", StringComparison.Ordinal) ||
            name.Any(char.IsControl) || name.IndexOfAny(['/', '\\', ':', '*', '?', '"', '<', '>', '|']) >= 0)
            return false;

        var stem = name.Split('.')[0].ToUpperInvariant();
        return stem is not ("CON" or "PRN" or "AUX" or "NUL" or "CLOCK$") &&
            !(stem.Length == 4 && (stem.StartsWith("COM", StringComparison.Ordinal) ||
                                   stem.StartsWith("LPT", StringComparison.Ordinal)) &&
                (stem[3] is >= '0' and <= '9' or '¹' or '²' or '³'));
    }

    private static bool IsExistingProfileDirectory(string root, string profileDirectory)
    {
        if (!IsSafeProfileDirectoryName(profileDirectory))
            return false;

        var fullPath = Path.GetFullPath(Path.Combine(root, profileDirectory));
        var rootPrefix = Path.EndsInDirectorySeparator(root) ? root : root + Path.DirectorySeparatorChar;
        if (!fullPath.StartsWith(rootPrefix, OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal) || !Directory.Exists(fullPath))
            return false;

        try
        {
            // Do not follow a profile-directory junction to some unrelated location.
            return (File.GetAttributes(fullPath) & FileAttributes.ReparsePoint) == 0;
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            return false;
        }
    }
}
