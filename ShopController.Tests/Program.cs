using System.Diagnostics;
using System.Text.Json;
using ShopController.Core;

// Deliberately exercises no real Chrome, network, cookies, passwords, or user profile.
var tests = new (string Name, Action Run)[]
{
    ("3 JD + 2 Taobao accounts need only 3 Chrome profiles", AllocationMinimalPacking),
    ("Taobao and Tmall share the Alibaba login realm", AllocationAlibabaIsolation),
    ("The same account across shops shares its profile", AllocationSameAccount),
    ("Account aliases normalize whitespace, case, and compatibility forms", AllocationAliasNormalization),
    ("Insufficient profile capacity produces no partial assignment", AllocationInsufficient),
    ("Valid existing bindings remain stable", AllocationStableBindings),
    ("Empty configuration needs no profiles", AllocationEmpty),
    ("Allocator is deterministic and every assignment is conflict-free", AllocationDeterministic),
    ("Duplicate profile names do not inflate available capacity", AllocationDuplicateProfiles),
    ("Duplicate shop IDs invalidate the entire allocation", AllocationDuplicateShopIds),
    ("Allocator satisfies capacity and isolation invariants across 80 fixtures", AllocationGeneratedFixtures),
    ("Shop validation rejects a conflicting same-platform profile", ValidationProfileConflict),
    ("Shop validation permits different-platform sharing", ValidationCrossPlatform),
    ("Shop validation accepts its own unchanged edit", ValidationEditing),
    ("Shop validation requires a name and account alias", ValidationRequiredFields),
    ("Shop validation permits an unassigned profile", ValidationUnbound),
    ("Shop validation rejects invalid platform and record identity", ValidationRecordIdentity),
    ("URL validation only accepts usable HTTP(S) URLs", ValidationUrls),
    ("Profile validation rejects path and switch injection", ValidationProfileNames),
    ("Configuration round-trips and retains previous good backup", ConfigRoundTrip),
    ("Malformed configuration is not overwritten", ConfigMalformedProtection),
    ("Unsupported configuration version is not overwritten", ConfigVersionProtection),
    ("Missing configuration version is rejected", ConfigMissingVersion),
    ("Chrome arguments retain exact profile and URL without a shell", ChromeArgumentBoundaries),
    ("Chrome launch validation rejects unsafe and missing inputs", ChromeRejectsUnsafe),
    ("Profile discovery reads metadata and skips unsafe entries", ChromeDiscoversMetadata),
    ("Profile discovery reports malformed JSON, missing metadata is empty", ChromeDiscoveryErrors),
    ("Profile discovery rejects structurally invalid metadata", ChromeDiscoveryShape),
    ("Known platform entry domains reject mislabeled realms without classifying lookalikes", ValidationKnownPlatformDomains),
};

int passed = 0;
foreach (var (name, run) in tests)
{
    try
    {
        run();
        passed++;
        Console.WriteLine($"PASS  {name}");
    }
    catch (Exception ex)
    {
        Console.Error.WriteLine($"FAIL  {name}\n      {ex.GetType().Name}: {ex.Message}");
    }
}
Console.WriteLine($"\n{passed}/{tests.Length} tests passed. No real browser or user profile was accessed.");
return passed == tests.Length ? 0 : 1;

static ShopEntry Shop(string name, ShopPlatform platform, string alias, string profile = "") => new()
{
    Id = Guid.NewGuid().ToString("D"),
    Name = name,
    Platform = platform,
    AccountAlias = alias,
    ProfileDirectory = profile,
    HomeUrl = "https://example.com/merchant",
    Notes = "Test-only local fixture",
};

static ProfileInfo[] Profiles(int count) => Enumerable.Range(0, count)
    .Select(i => new ProfileInfo(i == 0 ? "Default" : $"Profile {i}", $"Environment {i + 1}"))
    .ToArray();

static ShopEntry[] FiveShops() =>
[
    Shop("JD Shop A", ShopPlatform.JD, "jd-a"),
    Shop("JD Shop B", ShopPlatform.JD, "jd-b"),
    Shop("JD Shop C", ShopPlatform.JD, "jd-c"),
    Shop("Taobao Shop A", ShopPlatform.Taobao, "tb-a"),
    Shop("Taobao Shop B", ShopPlatform.Taobao, "tb-b"),
];

static void Check(bool condition, string message)
{
    if (!condition) throw new InvalidOperationException(message);
}

static void Equal<T>(T expected, T actual, string message)
{
    if (!EqualityComparer<T>.Default.Equals(expected, actual))
        throw new InvalidOperationException($"{message}: expected {expected}, actual {actual}");
}

static void Throws(Action action, string message)
{
    try { action(); }
    catch { return; }
    throw new InvalidOperationException(message);
}

static Dictionary<string, string> Map(AssignmentPlan plan) => plan.Assignments
    .ToDictionary(x => x.ShopId, x => x.ProfileDirectory);

static void AssertNoCollisions(IReadOnlyList<ShopEntry> shops, AssignmentPlan plan)
{
    Equal(shops.Count, plan.Assignments.Count, "All shops need exactly one assignment");
    var map = Map(plan);
    foreach (var realm in shops.GroupBy(s => PlatformCatalog.GetRealm(s.Platform)))
    {
        var profilesToAliases = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        foreach (var shop in realm)
        {
            string alias = shop.AccountAlias.Trim().Normalize(System.Text.NormalizationForm.FormKC).ToUpperInvariant();
            Check(map.ContainsKey(shop.Id), "Shop must have assignment");
            if (profilesToAliases.TryGetValue(map[shop.Id], out var previous))
                Equal(previous, alias, "Different identities in one realm must never share a profile");
            else profilesToAliases.Add(map[shop.Id], alias);
        }
    }
}

static void AllocationMinimalPacking()
{
    var shops = FiveShops();
    var plan = ProfileAllocator.Plan(shops, Profiles(3));
    Check(plan.CanApply, "Three profiles should be enough");
    Equal(3, plan.RequiredProfiles, "Minimum required profile count");
    Equal(3, plan.Assignments.Select(x => x.ProfileDirectory).Distinct().Count(), "Used profile count");
    AssertNoCollisions(shops, plan);
}

static void AllocationAlibabaIsolation()
{
    var shops = new[] { Shop("Taobao", ShopPlatform.Taobao, "alice"), Shop("Tmall", ShopPlatform.Tmall, "bob") };
    var plan = ProfileAllocator.Plan(shops, Profiles(2));
    Check(plan.CanApply, "Two profiles should be enough");
    Equal(2, plan.RequiredProfiles, "Different Taobao/Tmall identities need two profiles");
    AssertNoCollisions(shops, plan);
}

static void AllocationSameAccount()
{
    var shops = new[] { Shop("Taobao A", ShopPlatform.Taobao, "alice"), Shop("Tmall B", ShopPlatform.Tmall, "alice") };
    var plan = ProfileAllocator.Plan(shops, Profiles(1));
    Check(plan.CanApply, "The same Alibaba identity may share");
    Equal(1, plan.RequiredProfiles, "Shared identity count");
    Equal(1, plan.Assignments.Select(a => a.ProfileDirectory).Distinct().Count(), "Same identity uses one profile");
}

static void AllocationAliasNormalization()
{
    var shops = new[] { Shop("A", ShopPlatform.JD, "Alice"), Shop("B", ShopPlatform.JD, " ＡＬＩＣＥ ") };
    var plan = ProfileAllocator.Plan(shops, Profiles(1));
    Check(plan.CanApply, "Equivalent aliases should normalize");
    Equal(1, plan.RequiredProfiles, "Normalized identity count");
}

static void AllocationInsufficient()
{
    var plan = ProfileAllocator.Plan(FiveShops(), Profiles(2));
    Check(!plan.CanApply, "Two profiles cannot hold three JD identities");
    Equal(3, plan.RequiredProfiles, "Report the required capacity");
    Equal(0, plan.Assignments.Count, "No partial assignment is permitted");
    Check(plan.Warnings.Count > 0, "Insufficient capacity must be explained");
}

static void AllocationStableBindings()
{
    var shops = new[] { Shop("JD A", ShopPlatform.JD, "a", "Profile 2"), Shop("JD B", ShopPlatform.JD, "b", "Default"), Shop("Taobao", ShopPlatform.Taobao, "t", "Profile 2") };
    var plan = ProfileAllocator.Plan(shops, Profiles(3));
    Check(plan.CanApply, "Valid bindings can be planned");
    var map = Map(plan);
    foreach (var shop in shops) Equal(shop.ProfileDirectory, map[shop.Id], "Preserve valid existing binding");
    AssertNoCollisions(shops, plan);
}

static void AllocationEmpty()
{
    var plan = ProfileAllocator.Plan(Array.Empty<ShopEntry>(), Array.Empty<ProfileInfo>());
    Check(plan.CanApply, "Empty plan is valid");
    Equal(0, plan.RequiredProfiles, "Empty required count");
    Equal(0, plan.Assignments.Count, "Empty assignment count");
}

static void AllocationDeterministic()
{
    var shops = FiveShops().Concat(new[] { Shop("PDD A", ShopPlatform.Pdd, "p-a"), Shop("PDD B", ShopPlatform.Pdd, "p-b") }).ToArray();
    var a = ProfileAllocator.Plan(shops, Profiles(4));
    var b = ProfileAllocator.Plan(shops, Profiles(4));
    Check(a.CanApply && b.CanApply, "Both plans should work");
    Equal(string.Join("|", a.Assignments.Select(x => $"{x.ShopId}:{x.ProfileDirectory}")),
        string.Join("|", b.Assignments.Select(x => $"{x.ShopId}:{x.ProfileDirectory}")), "Plan should be deterministic");
    AssertNoCollisions(shops, a);
}

static void AllocationDuplicateProfiles()
{
    var pool = new[] { new ProfileInfo("Default", "Main"), new ProfileInfo("default", "Duplicate"), new ProfileInfo("Profile 1", "Second") };
    var plan = ProfileAllocator.Plan(FiveShops(), pool);
    Check(!plan.CanApply, "Case-insensitive duplicate profiles must not count twice");
    Equal(0, plan.Assignments.Count, "Insufficient distinct profiles yields no partial plan");
}

static void AllocationDuplicateShopIds()
{
    var shops = FiveShops();
    shops[1].Id = shops[0].Id;
    var plan = ProfileAllocator.Plan(shops, Profiles(3));
    Check(!plan.CanApply, "Duplicate IDs must make the plan invalid");
    Equal(0, plan.Assignments.Count, "Ambiguous plan must never be partly applied");
}

static void AllocationGeneratedFixtures()
{
    var random = new Random(20261028);
    for (int run = 0; run < 80; run++)
    {
        int jd = random.Next(0, 7), alibaba = random.Next(0, 7), pdd = random.Next(0, 7);
        var shops = new List<ShopEntry>();
        foreach (var (platform, count) in new[] { (ShopPlatform.JD, jd), (ShopPlatform.Taobao, alibaba), (ShopPlatform.Pdd, pdd) })
            for (int account = 0; account < count; account++)
            {
                int shopCount = random.Next(1, 4);
                for (int store = 0; store < shopCount; store++)
                    shops.Add(Shop($"{platform} {account} / {store}", platform == ShopPlatform.Taobao && store % 2 == 1 ? ShopPlatform.Tmall : platform,
                        $"account-{account}", random.Next(3) == 0 ? Profiles(6)[random.Next(6)].DirectoryName : ""));
            }
        int required = Math.Max(jd, Math.Max(alibaba, pdd));
        var plan = ProfileAllocator.Plan(shops, Profiles(6));
        Check(plan.CanApply, $"Generated case {run} should fit");
        Equal(required, plan.RequiredProfiles, $"Generated case {run} minimum");
        Equal(required, plan.Assignments.Select(a => a.ProfileDirectory).Distinct().Count(), $"Generated case {run} uses exactly minimum");
        AssertNoCollisions(shops, plan);
    }
}

static void ValidationProfileConflict()
{
    var existing = Shop("Existing", ShopPlatform.Taobao, "alice", "Default");
    var candidate = Shop("Candidate", ShopPlatform.Tmall, "bob", "Default");
    Check(Validation.ValidateShop(candidate, new[] { existing }) is not null, "Conflicting login identity must be rejected");
}

static void ValidationCrossPlatform()
{
    var existing = Shop("JD", ShopPlatform.JD, "alice", "Default");
    var candidate = Shop("Taobao", ShopPlatform.Taobao, "bob", "Default");
    Check(Validation.ValidateShop(candidate, new[] { existing }) is null, "Unrelated platform identities may share a profile");
}

static void ValidationEditing()
{
    var shop = Shop("Existing", ShopPlatform.JD, "alice", "Default");
    Check(Validation.ValidateShop(shop, new[] { shop }, shop.Id) is null, "An unchanged edit should remain valid");
}

static void ValidationRequiredFields()
{
    var shop = Shop("", ShopPlatform.JD, "alice");
    Check(Validation.ValidateShop(shop, Array.Empty<ShopEntry>()) is not null, "Name required");
    shop.Name = "Shop";
    shop.AccountAlias = " ";
    Check(Validation.ValidateShop(shop, Array.Empty<ShopEntry>()) is not null, "Account alias required");
}

static void ValidationUnbound()
{
    Check(Validation.ValidateShop(Shop("Pending", ShopPlatform.JD, "alias"), Array.Empty<ShopEntry>()) is null,
        "An unbound shop can be recorded before allocation");
}

static void ValidationRecordIdentity()
{
    var shop = Shop("Shop", (ShopPlatform)999, "alias");
    Check(Validation.ValidateShop(shop, Array.Empty<ShopEntry>()) is not null, "Unknown platform rejected");
    shop.Platform = ShopPlatform.JD;
    shop.Id = Guid.Empty.ToString("D");
    Check(Validation.ValidateShop(shop, Array.Empty<ShopEntry>()) is not null, "Empty GUID rejected");
    shop.Id = "not-a-guid";
    Check(Validation.ValidateShop(shop, Array.Empty<ShopEntry>()) is not null, "Invalid GUID rejected");
}

static void ValidationUrls()
{
    foreach (var url in new[] { "https://example.com/path?q=a%20b&x=%26", "http://localhost:8080/test", "https://example.com/中文", "https://example.com/orders#订单", "https://example.com/orders?name=a%20b&signed=%2B%2F#订单" })
        Check(Validation.ValidateUrl(url) is null, $"Valid URL rejected: {url}");
    foreach (var url in new[] { "", "not a url", "file:///C:/Windows/notepad.exe", "javascript:alert(1)", "data:text/html,test", "https://user:password@example.com/", "https://@example.com/", "https://example.com/%0D%0a", "https://example.com/%C2%85", "https://example.com/\\path", "https://example.com/\r\n--flag", "https://example.com/\u0000" })
        Check(Validation.ValidateUrl(url) is not null, $"Unsafe URL accepted: {JsonSerializer.Serialize(url)}");
}

static void ValidationProfileNames()
{
    foreach (var name in new[] { "Default", "Profile 1", "ShopController_123" })
        Check(Validation.ValidateProfileDirectory(name, false) is null, $"Valid profile rejected: {name}");
    foreach (var name in new[] { "", ".", "..", "../Default", "Profile/1", "Profile\\1", "C:\\Default", "--remote-debugging-port=9222", "Profile\n1" })
        Check(Validation.ValidateProfileDirectory(name, false) is not null, $"Unsafe profile accepted: {JsonSerializer.Serialize(name)}");
}

static void ConfigRoundTrip() => InTemp(root =>
{
    var path = Path.Combine(root, "settings", "shops.json");
    var store = new ConfigStore(path);
    Equal(0, store.Load().Shops.Count, "Missing config starts empty");
    var config = new AppConfig { Shops = [Shop("JD Original", ShopPlatform.JD, "a", "Default")] };
    const string originalUrl = "https://example.com/orders?name=a%20b&signed=%2B%2F#订单";
    config.Shops[0].HomeUrl = originalUrl;
    store.Save(config);
    Equal("JD Original", store.Load().Shops.Single().Name, "Round-trip name");
    Equal(originalUrl, store.Load().Shops.Single().HomeUrl, "Unicode fragment and signed query survive verbatim");
    config.Shops[0].Name = "JD Renamed";
    store.Save(config);
    Equal("JD Renamed", store.Load().Shops.Single().Name, "Updated name");
    Check(File.Exists(path + ".bak"), "Backup should exist after second save");
    Equal("JD Original", new ConfigStore(path + ".bak").Load().Shops.Single().Name, "Backup retains previous valid version");
    Check(!File.ReadAllText(path).Contains("cookie", StringComparison.OrdinalIgnoreCase), "Configuration contains no cookie material");
});

static void ConfigMalformedProtection() => InTemp(root =>
{
    var path = Path.Combine(root, "shops.json");
    const string corrupt = "{\"version\":1,broken";
    File.WriteAllText(path, corrupt);
    var store = new ConfigStore(path);
    Throws(() => store.Load(), "Malformed config should fail loudly");
    Throws(() => store.Save(new AppConfig()), "Saving must not overwrite malformed original");
    Equal(corrupt, File.ReadAllText(path), "Malformed original preserved byte-for-byte");
});

static void ConfigVersionProtection() => InTemp(root =>
{
    var path = Path.Combine(root, "shops.json");
    const string future = "{\"version\":99,\"shops\":[]}";
    File.WriteAllText(path, future);
    var store = new ConfigStore(path);
    Throws(() => store.Load(), "Future schema should be rejected");
    Throws(() => store.Save(new AppConfig()), "Saving must not downgrade unknown schema");
    Equal(future, File.ReadAllText(path), "Future schema preserved");
});

static void ConfigMissingVersion() => InTemp(root =>
{
    var path = Path.Combine(root, "shops.json");
    File.WriteAllText(path, "{\"shops\":[]}");
    Throws(() => new ConfigStore(path).Load(), "Version must be explicit");
});

static (string Exe, string UserData) ChromeFixture(string root)
{
    string exe = OperatingSystem.IsMacOS()
        ? Path.Combine(root, "Chrome test 中文", "Google Chrome.app", "Contents", "MacOS", "Google Chrome")
        : Path.Combine(root, "Chrome test 中文", "chrome.exe");
    Directory.CreateDirectory(Path.GetDirectoryName(exe)!);
    File.WriteAllText(exe, "TEST PLACEHOLDER - NEVER EXECUTE");
    if (OperatingSystem.IsMacOS())
        File.SetUnixFileMode(exe, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
    string userData = Path.Combine(root, "User Data 中文");
    Directory.CreateDirectory(Path.Combine(userData, "Default"));
    Directory.CreateDirectory(Path.Combine(userData, "Profile 1"));
    return (exe, userData);
}

static void ChromeArgumentBoundaries() => InTemp(root =>
{
    var f = ChromeFixture(root);
    const string url = "https://example.com/orders?query=a%20b&encoded=%26&next=https%3A%2F%2Fexample.com%2F#订单";
    ProcessStartInfo info = ChromeService.BuildStartInfo(f.Exe, f.UserData, "Profile 1", url);
    Equal(f.Exe, info.FileName, "Exact executable path");
    Check(!info.UseShellExecute, "No shell invocation");
    Equal("", info.Arguments, "Arguments must not be interpolated into a shell string");
    Check(info.ArgumentList.Contains(url), "Exact URL preserved as one argument");
    Check(ContainsArgument(info.ArgumentList, "--profile-directory", "Profile 1"), "Exact profile selected");
    Check(ContainsArgument(info.ArgumentList, "--user-data-dir", f.UserData), "Exact user data selected");
    Check(!info.ArgumentList.Any(a => a.Contains("remote-debugging", StringComparison.OrdinalIgnoreCase)), "No debugging port or pipe");
});

static bool ContainsArgument(IList<string> arguments, string key, string value)
{
    if (arguments.Contains(key + "=" + value)) return true;
    int index = arguments.IndexOf(key);
    return index >= 0 && index + 1 < arguments.Count && arguments[index + 1] == value;
}

static void ChromeRejectsUnsafe() => InTemp(root =>
{
    var f = ChromeFixture(root);
    foreach (var profile in new[] { "../Default", "Profile\\1", "--incognito", "Missing Profile" })
        Throws(() => ChromeService.BuildStartInfo(f.Exe, f.UserData, profile, "https://example.com"), "Invalid or missing profile must be rejected");
    foreach (var url in new[] { "javascript:alert(1)", "file:///C:/test", "https://a:b@example.com", "https://example.com/\n--flag" })
        Throws(() => ChromeService.BuildStartInfo(f.Exe, f.UserData, "Default", url), "Unsafe navigation must be rejected");
    Throws(() => ChromeService.BuildStartInfo("chrome.exe", f.UserData, "Default", "https://example.com"), "Relative executable rejected");
    string wrongExe = Path.Combine(root, "cmd.exe");
    File.WriteAllText(wrongExe, "TEST");
    Throws(() => ChromeService.BuildStartInfo(wrongExe, f.UserData, "Default", "https://example.com"), "Non-Chrome executable rejected");
    Throws(() => ChromeService.BuildStartInfo(f.Exe, "User Data", "Default", "https://example.com"), "Relative profile root rejected");
});

static void ChromeDiscoversMetadata() => InTemp(root =>
{
    var f = ChromeFixture(root);
    var cache = new Dictionary<string, object>
    {
        ["Default"] = new { name = "Main", user_name = "ignored@example.com" },
        ["Profile 1"] = new { name = "京东国际POP" },
        ["../evil"] = new { name = "Skip traversal" },
        ["Missing"] = new { name = "Skip missing directory" },
    };
    File.WriteAllText(Path.Combine(f.UserData, "Local State"), JsonSerializer.Serialize(new { profile = new { info_cache = cache } }));
    var profiles = ChromeService.DiscoverProfiles(f.UserData);
    Equal(2, profiles.Count, "Only existing safe profiles discovered");
    Check(profiles.Any(p => p.DirectoryName == "Default" && p.DisplayName == "Main"), "Display name from profile metadata");
    Check(profiles.Any(p => p.DirectoryName == "Profile 1" && p.DisplayName == "京东国际POP"), "Unicode profile name preserved");
    Check(!profiles.Any(p => p.DisplayName.Contains("@")), "No unrelated account metadata surfaced");
});

static void ChromeDiscoveryErrors() => InTemp(root =>
{
    var f = ChromeFixture(root);
    Equal(0, ChromeService.DiscoverProfiles(f.UserData).Count, "Missing metadata is empty");
    File.WriteAllText(Path.Combine(f.UserData, "Local State"), "broken json");
    Throws(() => ChromeService.DiscoverProfiles(f.UserData), "Malformed metadata must be reported");
});

static void ChromeDiscoveryShape() => InTemp(root =>
{
    var f = ChromeFixture(root);
    foreach (var text in new[] { "[]", "{\"profile\":[]}", "{\"profile\":{\"info_cache\":[]}}" })
    {
        File.WriteAllText(Path.Combine(f.UserData, "Local State"), text);
        Throws(() => ChromeService.DiscoverProfiles(f.UserData), "Unexpected metadata structure must be reported");
    }
});

static void InTemp(Action<string> action)
{
    string parent = Path.GetFullPath(Path.Combine(Path.GetTempPath(), "ShopController.Tests"));
    string root = Path.GetFullPath(Path.Combine(parent, Guid.NewGuid().ToString("N")));
    Directory.CreateDirectory(root);
    try { action(root); }
    finally
    {
        // Restrict recursive cleanup to this run's own GUID directory.
        string expectedParent = Path.TrimEndingDirectorySeparator(parent) + Path.DirectorySeparatorChar;
        if (!root.StartsWith(expectedParent, StringComparison.OrdinalIgnoreCase) || Path.GetFileName(root).Length != 32)
            throw new InvalidOperationException("Unexpected temporary cleanup target");
        Directory.Delete(root, recursive: true);
    }
}

static void ValidationKnownPlatformDomains()
{
    var domains = new (string Url, string Realm)[]
    {
        ("https://jd.com/", "JD"),
        ("https://shop.jd.com/#订单", "JD"),
        ("https://SHOP.JD.COM./orders", "JD"),
        ("https://jd.hk/", "JD"),
        ("https://seller.jd.hk/", "JD"),
        ("https://taobao.com/", "Alibaba"),
        ("https://myseller.taobao.com/orders", "Alibaba"),
        ("https://tmall.com/", "Alibaba"),
        ("https://seller.tmall.com/", "Alibaba"),
        ("https://pinduoduo.com/", "Pdd"),
        ("https://mms.pinduoduo.com/", "Pdd"),
    };
    foreach (var (url, realm) in domains)
    {
        foreach (var platform in Enum.GetValues<ShopPlatform>())
        {
            var shop = Shop("Domain fixture", platform, "test-account");
            shop.HomeUrl = url;
            var error = Validation.ValidateShop(shop, []);
            Equal(PlatformCatalog.GetRealm(platform) == realm, error is null,
                $"Known domain/platform classification: {platform} / {url}");
            Equal(url, shop.HomeUrl, "Platform checks must not rewrite the original URL");
        }
    }

    // These are unknown hosts, not known platform domains. Acceptance here only
    // verifies the documented unknown-domain policy, not trust in those hosts.
    foreach (var url in new[]
    {
        "https://notjd.com/", "https://jd.com.example.org/", "https://jd.hk.example.org/",
        "https://nottaobao.com/", "https://taobao.com.example.org/", "https://tmall.com.example.org/",
        "https://notpinduoduo.com/", "https://pinduoduo.com.example.org/",
        "https://example.com/taobao.com?next=https%3A%2F%2Fshop.jd.com%2F"
    })
    {
        var shop = Shop("Unknown domain fixture", ShopPlatform.Other, "test-account");
        shop.HomeUrl = url;
        Check(Validation.ValidateShop(shop, []) is null, $"Unknown domain was misclassified: {url}");
    }

    var existing = Shop("Alibaba existing", ShopPlatform.Taobao, "account-a", "Default");
    var mislabeled = Shop("Mislabeled JD", ShopPlatform.JD, "account-b", "Default");
    mislabeled.HomeUrl = "https://myseller.taobao.com/";
    Check(Validation.ValidateShop(mislabeled, [existing]) is not null,
        "A known Alibaba URL must not sidestep the realm conflict by using the JD label");
    mislabeled.Platform = ShopPlatform.Other;
    Check(Validation.ValidateShop(mislabeled, [existing]) is not null,
        "Other must not sidestep known platform domain classification");
}
