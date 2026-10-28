using System.Text;

namespace ShopController.Core;

public static class Validation
{
    public const int MaxNameLength = 100;
    public const int MaxAliasLength = 100;
    public const int MaxProfileLength = 128;
    public const int MaxUrlLength = 4096;
    public const int MaxNotesLength = 2000;

    public static string? ValidateShop(ShopEntry shop, IReadOnlyList<ShopEntry> existing,
        string? excludeId = null)
    {
        ArgumentNullException.ThrowIfNull(shop);
        ArgumentNullException.ThrowIfNull(existing);
        if (!Guid.TryParseExact(shop.Id, "D", out var id) || id == Guid.Empty)
            return "店铺 ID 必须为非空 GUID。";
        if (!Enum.IsDefined(shop.Platform)) return "店铺平台无效。";
        if (string.IsNullOrWhiteSpace(shop.Name)) return "请输入店铺名称。";
        if (shop.Name.Length > MaxNameLength || HasControlCharacters(shop.Name))
            return $"店铺名称最多 {MaxNameLength} 个字符且须为单行文本。";
        if (string.IsNullOrWhiteSpace(shop.AccountAlias)) return "请输入登录账号别名。";
        if (shop.AccountAlias.Length > MaxAliasLength || HasControlCharacters(shop.AccountAlias))
            return $"账号别名最多 {MaxAliasLength} 个字符且须为单行文本。";
        if (shop.Notes is null || shop.Notes.Length > MaxNotesLength ||
            shop.Notes.Any(c => char.IsControl(c) && c is not '\r' and not '\n' and not '\t'))
            return $"备注最多 {MaxNotesLength} 个字符，且只允许常规换行与制表符。";
        if (ValidateUrl(shop.HomeUrl) is { } urlError) return urlError;
        if (ValidateKnownPlatformHost(shop.Platform, new Uri(shop.HomeUrl)) is { } platformError)
            return platformError;
        if (ValidateProfileDirectory(shop.ProfileDirectory) is { } profileError) return profileError;

        foreach (var other in existing)
        {
            if (other is null) return "现有店铺列表含空记录。";
            if (excludeId is not null && string.Equals(other.Id, excludeId, StringComparison.OrdinalIgnoreCase))
                continue;
            if (string.Equals(shop.Id, other.Id, StringComparison.OrdinalIgnoreCase))
                return "店铺 ID 已存在。";
            if (string.IsNullOrEmpty(shop.ProfileDirectory) || string.IsNullOrEmpty(other.ProfileDirectory))
                continue;
            if (PlatformCatalog.GetRealm(shop.Platform) == PlatformCatalog.GetRealm(other.Platform) &&
                string.Equals(shop.ProfileDirectory, other.ProfileDirectory, StringComparison.OrdinalIgnoreCase) &&
                !string.Equals(NormalizeAlias(shop.AccountAlias), NormalizeAlias(other.AccountAlias), StringComparison.OrdinalIgnoreCase))
                return $"该 Chrome 资料已绑定同登录体系的另一账号（{other.Name}），请选择其他资料。";
        }
        return null;
    }

    public static string? ValidateUrl(string? url)
    {
        if (string.IsNullOrWhiteSpace(url)) return "请输入后台网址。";
        if (url.Length > MaxUrlLength || !string.Equals(url, url.Trim(), StringComparison.Ordinal) ||
            HasControlCharacters(url) || url.Contains('\\'))
            return $"后台网址最多 {MaxUrlLength} 个字符，且须去除空白和控制字符。";
        // Reject encoded C0/DEL controls as well as literal controls.
        for (var i = 0; i + 2 < url.Length; i++)
        {
            if (url[i] == '%' && byte.TryParse(url.AsSpan(i + 1, 2),
                    System.Globalization.NumberStyles.HexNumber, System.Globalization.CultureInfo.InvariantCulture,
                    out var value) && (value < 32 || value == 127))
                return "后台网址含编码后的控制字符。";
        }
        if (HasControlCharacters(Uri.UnescapeDataString(url)))
            return "后台网址含编码后的控制字符。";
        // IsWellFormedOriginalString rejects otherwise usable Unicode fragments
        // such as #订单. Validate the parsed URL without rewriting the original.
        if (!Uri.TryCreate(url, UriKind.Absolute, out var uri) ||
            (uri.Scheme != Uri.UriSchemeHttp && uri.Scheme != Uri.UriSchemeHttps) ||
            string.IsNullOrWhiteSpace(uri.Host))
            return "后台网址须为完整的 HTTP 或 HTTPS 地址。";
        if (!string.IsNullOrEmpty(uri.UserInfo)) return "后台网址中请勿包含用户名或密码。";
        // An empty user-info segment (https://@host/) is also rejected.
        var authorityStart = url.IndexOf("://", StringComparison.Ordinal) + 3;
        var authorityEnd = url.IndexOfAny(['/', '?', '#'], authorityStart);
        if (authorityEnd < 0) authorityEnd = url.Length;
        if (url.AsSpan(authorityStart, authorityEnd - authorityStart).Contains('@'))
            return "后台网址中请勿包含用户信息。";
        return null;
    }

    public static string? ValidateProfileDirectory(string? directory, bool allowEmpty = true)
    {
        if (directory is null) return "Chrome 资料目录须为字符串。";
        if (directory.Length == 0) return allowEmpty ? null : "请选择 Chrome 资料。";
        if (directory.Length > MaxProfileLength || string.IsNullOrWhiteSpace(directory) ||
            directory != directory.Trim() || directory[0] == '-' || directory.EndsWith('.') ||
            directory.Contains("..", StringComparison.Ordinal) || HasControlCharacters(directory) ||
            directory.IndexOfAny(['<', '>', ':', '"', '/', '\\', '|', '?', '*']) >= 0)
            return "Chrome 资料目录须为安全的单层目录名，例如 Default 或 Profile 1。";
        var basename = directory.Split('.')[0].ToUpperInvariant();
        if (basename is "CON" or "PRN" or "AUX" or "NUL" or "CLOCK$" ||
            (basename.Length == 4 && (basename.StartsWith("COM", StringComparison.Ordinal) ||
             basename.StartsWith("LPT", StringComparison.Ordinal)) &&
             (basename[3] is >= '1' and <= '9' or '\u00b9' or '\u00b2' or '\u00b3')))
            return "Chrome 资料目录使用了 Windows 保留名称。";
        return null;
    }

    // This catches entry-point labeling mistakes only. It does not classify
    // redirects, constrain later navigation, or establish the signed-in identity.
    private static string? ValidateKnownPlatformHost(ShopPlatform platform, Uri url)
    {
        var host = url.IdnHost.TrimEnd('.');
        string? realm = null;
        string? label = null;
        if (IsDomainOrSubdomain(host, "jd.com") || IsDomainOrSubdomain(host, "jd.hk"))
        {
            realm = "JD";
            label = "京东";
        }
        else if (IsDomainOrSubdomain(host, "taobao.com") || IsDomainOrSubdomain(host, "tmall.com"))
        {
            realm = "Alibaba";
            label = "淘宝或天猫";
        }
        else if (IsDomainOrSubdomain(host, "pinduoduo.com"))
        {
            realm = "Pdd";
            label = "拼多多";
        }
        return realm is not null && PlatformCatalog.GetRealm(platform) != realm
            ? $"后台网址属于已知的{label}域名，与所选平台不一致；请核对平台和网址。"
            : null;
    }

    private static bool IsDomainOrSubdomain(string host, string domain) =>
        string.Equals(host, domain, StringComparison.OrdinalIgnoreCase) ||
        host.EndsWith("." + domain, StringComparison.OrdinalIgnoreCase);

    internal static string NormalizeAlias(string? alias) => (alias ?? "").Trim().Normalize(NormalizationForm.FormKC);
    internal static bool HasControlCharacters(string text) => text.Any(char.IsControl);
}
