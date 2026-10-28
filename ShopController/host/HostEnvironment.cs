using System.Text.Json;

namespace ShopController.Host;

internal static class HostEnvironment
{
    internal const string Version = "1.0.0";
    internal const int ProtocolVersion = 1;
    internal static string Platform => OperatingSystem.IsWindows() ? "windows" : OperatingSystem.IsMacOS() ? "macos" : "unsupported";
    internal static bool SupportsPin => OperatingSystem.IsWindows();

    internal static object Capabilities() => new
    {
        hostVersion = Version,
        protocolVersion = ProtocolVersion,
        platform = Platform,
        capabilities = new { pin = SupportsPin }
    };

    internal static string ConfigPath() => OperatingSystem.IsMacOS()
        ? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Library", "Application Support", "ShopController", "config.json")
        : Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "ShopController", "config.json");

    /// <summary>Only the installed sidecar determines the allowed release extension identity.</summary>
    internal static string ReadAllowedOrigin(string directory)
    {
        var path = Path.Combine(directory, "host-identity.json");
        using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
        if (stream.Length is 0 or > 4096) throw new InvalidDataException("本地助手身份文件大小无效，请重新安装同版本助手。");
        using var document = JsonDocument.Parse(stream, new JsonDocumentOptions { MaxDepth = 4 });
        if (document.RootElement.ValueKind != JsonValueKind.Object)
            throw new InvalidDataException("本地助手身份文件应为对象。");
        var properties = document.RootElement.EnumerateObject().ToArray();
        if (properties.Length != 1 || properties[0].Name != "extensionId" || properties[0].Value.ValueKind != JsonValueKind.String)
            throw new InvalidDataException("本地助手身份文件只接受 extensionId。");
        var id = properties[0].Value.GetString()!;
        if (id.Length != 32 || id.Any(c => c is < 'a' or > 'p'))
            throw new InvalidDataException("本地助手扩展 ID 无效，请重新安装与商店扩展配套的助手。");
        return $"chrome-extension://{id}/";
    }
}
