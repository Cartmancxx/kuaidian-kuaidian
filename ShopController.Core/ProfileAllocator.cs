namespace ShopController.Core;

public static class ProfileAllocator
{
    private sealed class AccountGroup(string realm, string alias)
    {
        public string Realm { get; } = realm;
        public string Alias { get; } = alias;
        public List<ShopEntry> Shops { get; } = [];
        public Dictionary<string, int> Preferences { get; } = new(StringComparer.OrdinalIgnoreCase);
    }

    public static AssignmentPlan Plan(IReadOnlyList<ShopEntry> shops, IReadOnlyList<ProfileInfo> profiles)
    {
        ArgumentNullException.ThrowIfNull(shops);
        ArgumentNullException.ThrowIfNull(profiles);
        var plan = new AssignmentPlan();
        var groups = new List<AccountGroup>();
        var seenIds = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var shop in shops)
        {
            if (shop is null)
            {
                plan.Warnings.Add("店铺列表含空记录，请先修复配置。");
                return plan;
            }
            if (Validation.ValidateShop(shop, []) is { } error)
            {
                plan.Warnings.Add($"{shop.Name}：{error}");
                return plan;
            }
            if (!seenIds.Add(shop.Id))
            {
                plan.Warnings.Add("店铺 ID 重复，请先修复配置。");
                return plan;
            }
            var realm = PlatformCatalog.GetRealm(shop.Platform);
            var alias = Validation.NormalizeAlias(shop.AccountAlias);
            var group = groups.FirstOrDefault(g => g.Realm == realm &&
                string.Equals(g.Alias, alias, StringComparison.OrdinalIgnoreCase));
            if (group is null)
            {
                group = new AccountGroup(realm, alias);
                groups.Add(group);
            }
            group.Shops.Add(shop);
        }
        plan.RequiredProfiles = groups.GroupBy(g => g.Realm).Select(g => g.Count()).DefaultIfEmpty(0).Max();

        var available = new List<ProfileInfo>();
        var seenProfiles = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var profile in profiles)
        {
            if (profile is null || Validation.ValidateProfileDirectory(profile.DirectoryName, false) is not null)
            {
                plan.Warnings.Add("忽略了格式无效的 Chrome 资料目录。");
                continue;
            }
            if (seenProfiles.Add(profile.DirectoryName)) available.Add(profile);
        }
        if (available.Count < plan.RequiredProfiles)
        {
            plan.Warnings.Add($"至少需要 {plan.RequiredProfiles} 个 Chrome 资料，当前可用 {available.Count} 个；请先在 Chrome 创建资料并刷新。本次不会部分应用。");
            return plan;
        }
        if (shops.Count == 0)
        {
            plan.CanApply = true;
            return plan;
        }

        var unbound = 0;
        foreach (var group in groups)
        {
            foreach (var shop in group.Shops)
            {
                if (string.IsNullOrEmpty(shop.ProfileDirectory)) { unbound++; continue; }
                if (!seenProfiles.Contains(shop.ProfileDirectory))
                {
                    plan.Warnings.Add($"{shop.Name} 原绑定的资料不在可用列表中，将重新分配。");
                    continue;
                }
                group.Preferences.TryGetValue(shop.ProfileDirectory, out var count);
                group.Preferences[shop.ProfileDirectory] = count + 1;
            }
        }
        if (unbound > 0) plan.Warnings.Add($"{unbound} 个店铺尚未绑定资料；应用完整计划后生效。");

        // Select exactly the minimum number of profiles. Marginal preference
        // coverage favors existing bindings; input order deterministically breaks ties.
        var pool = new List<ProfileInfo>();
        while (pool.Count < plan.RequiredProfiles)
        {
            ProfileInfo? best = null;
            var bestScore = -1;
            foreach (var candidate in available.Where(p => !pool.Contains(p)))
            {
                var score = 0;
                foreach (var group in groups)
                {
                    var currentBest = pool.Select(p => Weight(group, p.DirectoryName)).DefaultIfEmpty(0).Max();
                    score += Math.Max(0, Weight(group, candidate.DirectoryName) - currentBest);
                }
                if (score > bestScore) { best = candidate; bestScore = score; }
            }
            pool.Add(best!);
        }

        var assigned = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        foreach (var realmGroups in groups.GroupBy(g => g.Realm))
        {
            var realm = realmGroups.ToList();
            var columns = BestAssignment(realm, pool);
            for (var i = 0; i < realm.Count; i++)
                foreach (var shop in realm[i].Shops)
                    assigned.Add(shop.Id, pool[columns[i]].DirectoryName);
        }
        var changed = shops.Count(s => !string.IsNullOrEmpty(s.ProfileDirectory) &&
            !string.Equals(s.ProfileDirectory, assigned[s.Id], StringComparison.OrdinalIgnoreCase));
        if (changed > 0) plan.Warnings.Add($"为保持最少资料数并消除账号冲突，将调整 {changed} 个已有绑定；请确认计划。调整后可能需要在对应资料中重新登录。");
        plan.Assignments = shops.Select(s => new ProfileAssignment(s.Id, assigned[s.Id])).ToList();
        plan.CanApply = true;
        return plan;
    }

    private static int Weight(AccountGroup group, string profile) => group.Preferences.GetValueOrDefault(profile);

    // Rectangular Hungarian assignment: each account in a realm gets a distinct
    // profile, maximizing how many existing shop bindings survive within the pool.
    private static int[] BestAssignment(List<AccountGroup> groups, List<ProfileInfo> profiles)
    {
        var n = groups.Count;
        var m = profiles.Count;
        var u = new long[n + 1];
        var v = new long[m + 1];
        var p = new int[m + 1];
        var way = new int[m + 1];
        for (var i = 1; i <= n; i++)
        {
            p[0] = i;
            var j0 = 0;
            var min = Enumerable.Repeat(long.MaxValue / 4, m + 1).ToArray();
            var used = new bool[m + 1];
            do
            {
                used[j0] = true;
                var i0 = p[j0];
                var delta = long.MaxValue / 4;
                var j1 = 0;
                for (var j = 1; j <= m; j++)
                {
                    if (used[j]) continue;
                    var cost = -Weight(groups[i0 - 1], profiles[j - 1].DirectoryName) - u[i0] - v[j];
                    if (cost < min[j]) { min[j] = cost; way[j] = j0; }
                    if (min[j] < delta) { delta = min[j]; j1 = j; }
                }
                for (var j = 0; j <= m; j++)
                    if (used[j]) { u[p[j]] += delta; v[j] -= delta; }
                    else min[j] -= delta;
                j0 = j1;
            } while (p[j0] != 0);
            do
            {
                var j1 = way[j0];
                p[j0] = p[j1];
                j0 = j1;
            } while (j0 != 0);
        }
        var assignment = new int[n];
        for (var j = 1; j <= m; j++)
            if (p[j] > 0) assignment[p[j] - 1] = j - 1;
        return assignment;
    }
}
