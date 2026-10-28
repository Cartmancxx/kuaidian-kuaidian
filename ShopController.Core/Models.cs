namespace ShopController.Core;

public enum ShopPlatform { JD, Taobao, Tmall, Pdd, Other }

public sealed class ShopEntry
{
    public string Id { get; set; } = Guid.NewGuid().ToString("D");
    public string Name { get; set; } = "";
    public ShopPlatform Platform { get; set; } = ShopPlatform.JD;
    public string AccountAlias { get; set; } = "";
    public string ProfileDirectory { get; set; } = "";
    public string HomeUrl { get; set; } = "";
    public string Notes { get; set; } = "";
    public DateTimeOffset? LastOpenedAt { get; set; }
}

public sealed class AppConfig
{
    public int Version { get; set; } = 1;
    public string ChromeExecutable { get; set; } = "";
    public string UserDataRoot { get; set; } = "";
    public List<ShopEntry> Shops { get; set; } = [];
}

public sealed record ProfileInfo(string DirectoryName, string DisplayName);
public sealed record ProfileAssignment(string ShopId, string ProfileDirectory);

public sealed class AssignmentPlan
{
    public int RequiredProfiles { get; set; }
    public bool CanApply { get; set; }
    public List<ProfileAssignment> Assignments { get; set; } = [];
    public List<string> Warnings { get; set; } = [];
}
