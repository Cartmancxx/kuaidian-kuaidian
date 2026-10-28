using System.Collections.Concurrent;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace ShopController.Core;

public sealed class ConfigStore
{
    private const int MaxConfigBytes = 4 * 1024 * 1024;
    private static readonly ConcurrentDictionary<string, object> Locks = new(StringComparer.OrdinalIgnoreCase);
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        PropertyNameCaseInsensitive = false,
        WriteIndented = true,
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
        MaxDepth = 32,
        Converters = { new JsonStringEnumConverter<ShopPlatform>(allowIntegerValues: false) }
    };
    private readonly string _path;
    private readonly object _gate;

    public ConfigStore(string path)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(path);
        _path = Path.GetFullPath(path);
        _gate = Locks.GetOrAdd(_path, _ => new object());
    }

    public AppConfig Load()
    {
        lock (_gate)
        {
            if (Directory.Exists(_path)) throw new IOException($"配置路径指向目录：{_path}");
            return File.Exists(_path) ? ReadValidated() : new AppConfig();
        }
    }

    public void Save(AppConfig config)
    {
        ArgumentNullException.ThrowIfNull(config);
        lock (_gate)
        {
            ValidateConfig(config);
            if (Directory.Exists(_path)) throw new IOException($"配置路径指向目录：{_path}");
            // Never turn a corrupt/unknown existing document into an empty new one.
            if (File.Exists(_path)) _ = ReadValidated();
            var bytes = JsonSerializer.SerializeToUtf8Bytes(config, JsonOptions);
            if (bytes.Length > MaxConfigBytes) throw new InvalidDataException("配置文件超过大小限制。");
            var directory = Path.GetDirectoryName(_path)!;
            Directory.CreateDirectory(directory);
            var temporary = Path.Combine(directory, $".{Path.GetFileName(_path)}.{Guid.NewGuid():N}.tmp");
            try
            {
                var options = new FileStreamOptions
                {
                    Mode = FileMode.CreateNew, Access = FileAccess.Write, Share = FileShare.None,
                    BufferSize = 4096, Options = FileOptions.WriteThrough
                };
                // Restrict only the new file; never change an arbitrary existing parent directory.
                if (!OperatingSystem.IsWindows()) options.UnixCreateMode = UnixFileMode.UserRead | UnixFileMode.UserWrite;
                using (var stream = new FileStream(temporary, options))
                {
                    stream.Write(bytes);
                    stream.Flush(flushToDisk: true);
                }
                if (File.Exists(_path)) File.Replace(temporary, _path, _path + ".bak");
                else File.Move(temporary, _path); // No overwrite if another writer creates it.
            }
            finally
            {
                if (File.Exists(temporary)) File.Delete(temporary);
            }
        }
    }

    private AppConfig ReadValidated()
    {
        try
        {
            using var stream = new FileStream(_path, FileMode.Open, FileAccess.Read, FileShare.Read);
            if (stream.Length > MaxConfigBytes) throw new InvalidDataException("配置文件超过大小限制。");
            using var document = JsonDocument.Parse(stream, new JsonDocumentOptions { MaxDepth = 32 });
            if (document.RootElement.ValueKind != JsonValueKind.Object)
                throw new InvalidDataException("配置根节点须为对象。");
            RejectDuplicateProperties(document.RootElement);
            if (!document.RootElement.TryGetProperty("version", out var version) ||
                !version.TryGetInt32(out var number) || number != 1)
                throw new InvalidDataException("配置版本缺失或未知；仅支持 version=1。");
            var config = document.RootElement.Deserialize<AppConfig>(JsonOptions)
                ?? throw new InvalidDataException("配置内容为空。");
            ValidateConfig(config);
            return config;
        }
        catch (Exception ex) when (ex is JsonException or InvalidDataException or ArgumentException or InvalidOperationException)
        {
            throw new InvalidDataException($"配置文件无效，已保留原文件：{_path}。{ex.Message}", ex);
        }
    }

    private static void ValidateConfig(AppConfig config)
    {
        if (config.Version != 1) throw new InvalidDataException("仅支持配置版本 1。");
        if (config.ChromeExecutable is null || config.UserDataRoot is null ||
            config.ChromeExecutable.Length > 32767 || config.UserDataRoot.Length > 32767 ||
            Validation.HasControlCharacters(config.ChromeExecutable) || Validation.HasControlCharacters(config.UserDataRoot))
            throw new InvalidDataException("Chrome 路径或用户数据路径无效。");
        if (config.Shops is null || config.Shops.Count > 1000)
            throw new InvalidDataException("店铺列表为空值或超过 1000 条限制。");
        var ids = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var shop in config.Shops)
        {
            if (shop is null) throw new InvalidDataException("店铺列表含空记录。");
            if (!ids.Add(shop.Id)) throw new InvalidDataException("店铺 ID 重复。");
            if (Validation.ValidateShop(shop, config.Shops, shop.Id) is { } error)
                throw new InvalidDataException($"店铺“{shop.Name}”：{error}");
        }
    }

    private static void RejectDuplicateProperties(JsonElement element)
    {
        if (element.ValueKind == JsonValueKind.Object)
        {
            var names = new HashSet<string>(StringComparer.Ordinal);
            foreach (var property in element.EnumerateObject())
            {
                if (!names.Add(property.Name)) throw new InvalidDataException($"配置包含重复字段：{property.Name}");
                RejectDuplicateProperties(property.Value);
            }
        }
        else if (element.ValueKind == JsonValueKind.Array)
            foreach (var item in element.EnumerateArray()) RejectDuplicateProperties(item);
    }
}
