using System.Buffers.Binary;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using ShopController.Core;

namespace ShopController.Host;

internal static class Program
{
    // Fixture identity retained for test source compatibility, never a runtime fallback.
    internal const string Origin = "chrome-extension://hadeebhijljjdebkaiaglaeipajnnind/";
    internal static readonly JsonSerializerOptions Json = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        PropertyNameCaseInsensitive = true,
        Converters = { new JsonStringEnumConverter() }
    };

    public static int Main(string[] args)
    {
        // Installation is a separate, explicit local invocation. These commands are
        // never accepted as native-messaging actions or inferred from message data.
        if (args.Length > 0 && args[0] is "--install-user" or "--uninstall-user")
        {
            if (!OperatingSystem.IsWindows())
            {
                Console.Error.WriteLine("此安装命令适用于 Windows；macOS 请使用随包安装程序。");
                return 2;
            }
            return WindowsInstaller.Run(args.Skip(1).ToArray(), args[0] == "--uninstall-user");
        }
        var testMode = args.Length == 2 && args[0] == "--protocol-test";
        var diagnose = args.Length == 1 && args[0] == "--diagnose";
        if (!testMode && !diagnose)
        {
            try
            {
                var expectedOrigin = HostEnvironment.ReadAllowedOrigin(AppContext.BaseDirectory);
                if (args.Length == 0 || args[0] != expectedOrigin) throw new InvalidDataException("调用来源与本地助手登记不匹配。");
            }
            catch (Exception ex) when (ex is IOException or InvalidDataException or UnauthorizedAccessException or JsonException)
            {
                Console.Error.WriteLine("此程序由配套店铺控制器扩展调用。" + ex.Message);
                return 2;
            }
        }
        var path = testMode ? Path.GetFullPath(args[1]) : HostEnvironment.ConfigPath();
        var parentWindow = testMode || diagnose || !OperatingSystem.IsWindows() ? 0 : WindowPinning.ParseParentHandle(args.Skip(1));
        var dispatcher = new Dispatcher(path, testMode, parentWindow);
        if (diagnose)
        {
            Console.WriteLine(JsonSerializer.Serialize(dispatcher.Handle(JsonSerializer.SerializeToElement(new { action = "get_state" }, Json)), Json));
            return 0;
        }
        using var input = Console.OpenStandardInput();
        using var output = Console.OpenStandardOutput();
        try
        {
            while (true)
            {
                var header = new byte[4];
                var first = input.ReadByte();
                if (first < 0) break;
                header[0] = (byte)first;
                input.ReadExactly(header.AsSpan(1));
                var length = BinaryPrimitives.ReadUInt32LittleEndian(header);
                if (length is 0 or > 262144) throw new InvalidDataException("消息长度超出允许范围。");
                var body = new byte[(int)length];
                input.ReadExactly(body);
                object reply;
                try
                {
                    using var document = JsonDocument.Parse(body, new JsonDocumentOptions { MaxDepth = 24 });
                    reply = dispatcher.Handle(document.RootElement);
                }
                catch (Exception ex) when (ex is JsonException or InvalidOperationException)
                {
                    reply = new { ok = false, error = "请求格式有误。" };
                }
                var result = JsonSerializer.SerializeToUtf8Bytes(reply, Json);
                if (result.Length > 1_000_000) result = JsonSerializer.SerializeToUtf8Bytes(new { ok = false, error = "配置或资料列表过大，请先从备份恢复较小的配置。原文件未修改。" }, Json);
                BinaryPrimitives.WriteUInt32LittleEndian(header, (uint)result.Length);
                output.Write(header);
                output.Write(result);
                output.Flush();
            }
            return 0;
        }
        catch (Exception ex)
        {
            // Stdout is exclusively the Chrome native messaging protocol.
            Console.Error.WriteLine(ex.Message);
            return 1;
        }
    }
}

internal sealed class Dispatcher(string configPath, bool testMode, nint parentWindow = default)
{
    private readonly ConfigStore store = new(configPath);
    private readonly string mutexName = (OperatingSystem.IsWindows() ? "Local\\" : "") + "ShopController_" +
        Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(OperatingSystem.IsWindows() ? configPath.ToUpperInvariant() : configPath)))[..24];

    public object Handle(JsonElement request)
    {
        using var mutex = new Mutex(false, mutexName);
        var locked = false;
        try
        {
            if (request.ValueKind != JsonValueKind.Object) throw new InvalidDataException("请求应为对象。");
            var action = RequiredString(request, "action");
            if (action == "get_capabilities") return new { ok = true, data = HostEnvironment.Capabilities() };
            if (action is "get_launcher_pin" or "set_launcher_pin")
            {
                // These operations do not depend on shop configuration and must remain usable
                // even if a configuration file needs repair. JSON never supplies a window handle.
                var allowedFields = action == "set_launcher_pin" ? new[] { "action", "enabled" } : new[] { "action" };
                if (request.EnumerateObject().Any(property => !allowedFields.Contains(property.Name, StringComparer.Ordinal)))
                    throw new InvalidDataException("置顶请求只接受操作名和布尔开关，不接受窗口句柄或其他目标参数。");
                bool? enabled = null;
                if (action == "set_launcher_pin")
                {
                    if (!request.TryGetProperty("enabled", out var value) || value.ValueKind is not (JsonValueKind.True or JsonValueKind.False))
                        throw new InvalidDataException("置顶开关必须为布尔值。");
                    enabled = value.GetBoolean();
                }
                // Test runs must never reach user32, including read-only window discovery.
                if (testMode) return new { ok = false, testOnly = true, error = "协议测试模式不读取或修改真实窗口置顶状态。" };
                if (!HostEnvironment.SupportsPin) return new { ok = false, unsupported = true, error = "当前系统使用普通独立小窗，不启用置顶。" };
                var pinned = enabled.HasValue ? WindowPinning.SetPinned(parentWindow, enabled.Value) : WindowPinning.GetPinned(parentWindow);
                return new { ok = true, data = new { pinned } };
            }
            try { locked = mutex.WaitOne(TimeSpan.FromSeconds(8)); }
            catch (AbandonedMutexException) { locked = true; }
            if (!locked) throw new InvalidOperationException("另一个控制器正在保存，请稍后重试。");
            var config = store.Load();
            var root = Root(config);
            switch (action)
            {
                case "get_state": return new { ok = true, data = State(config) };
                case "plan_assignments":
                    var profiles = SelectedProfiles(request, root);
                    var plan = ProfileAllocator.Plan(config.Shops, profiles);
                    return new { ok = true, data = new { plan, revision = Revision(config), planToken = PlanToken(config, profiles, plan) } };
                case "save_shop":
                    CheckRevision(request, config);
                    if (config.Shops.Count >= 300 && !config.Shops.Any(s => s.Id == GetString(request.GetProperty("shop"), "id")))
                        throw new InvalidDataException("第一版最多管理 300 个入口。");
                    var shop = request.GetProperty("shop").Deserialize<ShopEntry>(Program.Json) ?? throw new InvalidDataException("店铺数据缺失。");
                    if (string.IsNullOrWhiteSpace(shop.Id)) shop.Id = Guid.NewGuid().ToString("D");
                    shop.Name = shop.Name.Trim();
                    shop.AccountAlias = shop.AccountAlias.Trim();
                    shop.HomeUrl = shop.HomeUrl.Trim();
                    shop.Notes = shop.Notes.Trim();
                    var error = Validation.ValidateShop(shop, config.Shops, shop.Id);
                    if (error != null) throw new InvalidDataException(error);
                    if (!string.IsNullOrEmpty(shop.ProfileDirectory) && !ChromeService.DiscoverProfiles(root).Any(p => p.DirectoryName == shop.ProfileDirectory))
                        throw new InvalidDataException("所选 Chrome 资料不存在，请刷新资料列表。");
                    var index = config.Shops.FindIndex(s => s.Id == shop.Id);
                    shop.LastOpenedAt = index >= 0 ? config.Shops[index].LastOpenedAt : null;
                    if (index >= 0) config.Shops[index] = shop; else config.Shops.Add(shop);
                    SaveBounded(config);
                    return new { ok = true, data = State(config) };
                case "delete_shop":
                    CheckRevision(request, config);
                    var deleteId = RequiredString(request, "id");
                    if (config.Shops.RemoveAll(s => s.Id == deleteId) == 0) throw new InvalidDataException("店铺入口已不存在。");
                    SaveBounded(config);
                    return new { ok = true, data = State(config) };
                case "apply_plan":
                    CheckRevision(request, config);
                    var currentProfiles = SelectedProfiles(request, root);
                    var currentPlan = ProfileAllocator.Plan(config.Shops, currentProfiles);
                    if (GetString(request, "planToken") != PlanToken(config, currentProfiles, currentPlan))
                        throw new InvalidOperationException("Chrome 资料或配对方案已变化，请重新预览后再确认。");
                    if (!currentPlan.CanApply) throw new InvalidDataException("现有资料数量不足，未应用配对。");
                    foreach (var assignment in currentPlan.Assignments)
                        config.Shops.Single(s => s.Id == assignment.ShopId).ProfileDirectory = assignment.ProfileDirectory;
                    foreach (var item in config.Shops)
                    {
                        var validation = Validation.ValidateShop(item, config.Shops, item.Id);
                        if (validation != null) throw new InvalidDataException(validation);
                    }
                    SaveBounded(config);
                    return new { ok = true, data = State(config) };
                case "save_settings":
                    CheckRevision(request, config);
                    var executable = GetString(request, "chromeExecutable").Trim();
                    var newRoot = GetString(request, "userDataRoot").Trim();
                    if (executable.Length != 0) _ = ChromeService.ValidateChromeExecutable(executable);
                    if (newRoot.Length != 0 && (!Path.IsPathFullyQualified(newRoot) || !Directory.Exists(newRoot)))
                        throw new InvalidDataException("Chrome 资料根目录不存在。");
                    _ = ChromeService.DiscoverProfiles(newRoot.Length == 0 ? ChromeService.DefaultUserDataRoot() : newRoot);
                    config.ChromeExecutable = executable;
                    config.UserDataRoot = newRoot;
                    SaveBounded(config);
                    return new { ok = true, data = State(config) };
                case "open_shop":
                    CheckRevision(request, config);
                    var selected = config.Shops.SingleOrDefault(s => s.Id == RequiredString(request, "id")) ?? throw new InvalidDataException("店铺入口不存在。");
                    var selectedError = Validation.ValidateShop(selected, config.Shops, selected.Id);
                    if (selectedError != null) throw new InvalidDataException(selectedError);
                    if (string.IsNullOrWhiteSpace(selected.ProfileDirectory)) throw new InvalidDataException("请先给此店铺绑定 Chrome 资料。");
                    var chrome = Executable(config);
                    if (string.IsNullOrEmpty(chrome)) throw new InvalidDataException("尚未找到 Chrome，请在设置中指定路径。");
                    if (!ChromeService.DiscoverProfiles(root).Any(p => p.DirectoryName == selected.ProfileDirectory))
                        throw new InvalidDataException("资料目录已变化，请刷新并重新绑定。");
                    if (testMode)
                    {
                        var start = ChromeService.BuildStartInfo(chrome, root, selected.ProfileDirectory, selected.HomeUrl);
                        return new { ok = true, data = new { opened = false, testOnly = true, arguments = start.ArgumentList.ToArray() } };
                    }
                    ChromeService.Open(chrome, root, selected.ProfileDirectory, selected.HomeUrl);
                    // The successful process start is not proof of login, focus or navigation completion.
                    selected.LastOpenedAt = DateTimeOffset.UtcNow;
                    string? saveWarning = null;
                    try { SaveBounded(config); } catch (Exception ex) { saveWarning = "Chrome 打开请求已发出，但最近使用时间未保存：" + ex.Message; }
                    return new { ok = true, data = new { opened = true, message = "已向指定 Chrome 资料发送打开请求；请核对后台实际账号。", warning = saveWarning } };
                default: throw new InvalidDataException("未知操作。");
            }
        }
        catch (Exception ex)
        {
            return new { ok = false, error = ex.Message };
        }
        finally { if (locked) mutex.ReleaseMutex(); }
    }

    private object State(AppConfig config)
    {
        var warnings = new List<string>();
        IReadOnlyList<ProfileInfo> profiles = [];
        try { profiles = ChromeService.DiscoverProfiles(Root(config)); }
        catch (Exception ex) { warnings.Add("读取 Chrome 资料列表失败：" + ex.Message); }
        var executable = Executable(config);
        if (string.IsNullOrEmpty(executable)) warnings.Add("尚未找到 Chrome，请在设置中指定本机 Chrome 程序的完整路径。");
        return new
        {
            config,
            profiles,
            chromeExecutable = executable,
            userDataRoot = Root(config),
            revision = Revision(config),
            warnings,
            testMode,
            hostVersion = HostEnvironment.Version,
            protocolVersion = HostEnvironment.ProtocolVersion,
            platform = HostEnvironment.Platform,
            capabilities = new { pin = HostEnvironment.SupportsPin },
            platforms = Enum.GetValues<ShopPlatform>().Select(p => new { value = p.ToString(), label = PlatformCatalog.GetLabel(p), realm = PlatformCatalog.GetRealm(p), defaultUrl = PlatformCatalog.GetDefaultUrl(p) })
        };
    }
    private void SaveBounded(AppConfig config)
    {
        if (JsonSerializer.SerializeToUtf8Bytes(State(config), Program.Json).Length > 800_000)
            throw new InvalidDataException("配置内容过长，请缩短备注或减少入口；本次修改未保存。");
        store.Save(config);
    }
    private static IReadOnlyList<ProfileInfo> SelectedProfiles(JsonElement request, string root)
    {
        var profiles = ChromeService.DiscoverProfiles(root);
        if (!request.TryGetProperty("profileDirectories", out var selected)) return profiles;
        if (selected.ValueKind != JsonValueKind.Array || selected.GetArrayLength() > 300) throw new InvalidDataException("资料选择无效。");
        var names = selected.EnumerateArray().Select(x => x.GetString() ?? "").Distinct(StringComparer.OrdinalIgnoreCase).ToHashSet(StringComparer.OrdinalIgnoreCase);
        if (names.Any(name => !profiles.Any(p => string.Equals(p.DirectoryName, name, StringComparison.OrdinalIgnoreCase))))
            throw new InvalidDataException("选择的 Chrome 资料已变化，请刷新列表。");
        return profiles.Where(p => names.Contains(p.DirectoryName)).ToArray();
    }
    private static string PlanToken(AppConfig config, IReadOnlyList<ProfileInfo> profiles, AssignmentPlan plan) =>
        Convert.ToHexString(SHA256.HashData(JsonSerializer.SerializeToUtf8Bytes(new { revision = Revision(config), profiles = profiles.OrderBy(p => p.DirectoryName, StringComparer.OrdinalIgnoreCase), plan }, Program.Json)));
    private static string Root(AppConfig config) => string.IsNullOrWhiteSpace(config.UserDataRoot) ? ChromeService.DefaultUserDataRoot() : config.UserDataRoot;
    private static string? Executable(AppConfig config) => string.IsNullOrWhiteSpace(config.ChromeExecutable) ? ChromeService.DetectChromeExecutable() : config.ChromeExecutable;
    private static string Revision(AppConfig config) => Convert.ToHexString(SHA256.HashData(JsonSerializer.SerializeToUtf8Bytes(config, Program.Json)));
    private static void CheckRevision(JsonElement request, AppConfig config)
    {
        if (GetString(request, "revision") != Revision(config)) throw new InvalidOperationException("配置已在其他窗口更新，请刷新后重试。");
    }
    private static string GetString(JsonElement item, string key) => item.TryGetProperty(key, out var value) && value.ValueKind == JsonValueKind.String ? value.GetString() ?? "" : "";
    private static string RequiredString(JsonElement item, string key)
    {
        var result = GetString(item, key);
        return string.IsNullOrWhiteSpace(result) ? throw new InvalidDataException("缺少字段：" + key) : result;
    }
}
