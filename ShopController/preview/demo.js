// Explicit preview mode only. No browser account data, native calls, storage or network.
const platforms = [
  { value: 'JD', label: '京东', realm: 'jd', defaultUrl: 'https://shop.jd.com/' },
  { value: 'Taobao', label: '淘宝', realm: 'alibaba', defaultUrl: 'https://myseller.taobao.com/' },
  { value: 'Tmall', label: '天猫', realm: 'alibaba', defaultUrl: 'https://myseller.taobao.com/' },
  { value: 'Pdd', label: 'PDD', realm: 'pdd', defaultUrl: 'https://mms.pinduoduo.com/' },
  { value: 'Other', label: '其他', realm: 'other', defaultUrl: '' }
];
const profiles = [1, 2, 3].map(n => ({ directoryName: `Profile ${n}`, displayName: `电商资料 ${n}` }));
const shops = [
 ['京东国际POP', 'JD', '京东账号 A', 'Profile 1', '国际店 · 示例'],
 ['京东POP', 'JD', '京东账号 B', 'Profile 2', '日常运营 · 示例'],
 ['京东主店', 'JD', '京东账号 C', 'Profile 3', '主店 · 示例'],
 ['淘宝旗舰店', 'Taobao', '淘宝账号 A', 'Profile 1', '与京东国际店共用资料 · 示例'],
 ['天猫专营店', 'Tmall', '淘宝账号 B', 'Profile 2', '与京东POP共用资料 · 示例']
].map((row, i) => ({ id: `00000000-0000-4000-8000-00000000000${i}`, name: row[0], platform: row[1], accountAlias: row[2], profileDirectory: row[3], notes: row[4], homeUrl: platforms.find(p => p.value === row[1]).defaultUrl, lastOpenedAt: null }));
let revision = 1;
const config = { version: 1, chromeExecutable: '', userDataRoot: '', shops };
const snapshot = () => structuredClone({ config, profiles, platforms, revision: String(revision), warnings: [], chromeExecutable: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', userDataRoot: 'C:\\示例\\Chrome\\User Data', testMode: true });
const realm = shop => platforms.find(p => p.value === shop.platform)?.realm;
function plan(dirs) {
  const grouped = new Map();
  for (const shop of config.shops) {
    const key = realm(shop);
    if (!grouped.has(key)) grouped.set(key, new Map());
    const accounts = grouped.get(key);
    const alias = shop.accountAlias.trim().normalize('NFKC').toLowerCase();
    if (!accounts.has(alias)) accounts.set(alias, []);
    accounts.get(alias).push(shop);
  }
  const requiredProfiles = Math.max(0, ...[...grouped.values()].map(accounts => accounts.size));
  if (dirs.length < requiredProfiles) return { requiredProfiles, canApply: false, assignments: [], warnings: [`至少选择 ${requiredProfiles} 份可用于电商的资料。`] };
  const assignments = [];
  for (const accounts of grouped.values()) {
    let i = 0;
    for (const items of accounts.values()) { for (const shop of items) assignments.push({ shopId: shop.id, profileDirectory: dirs[i] }); i++; }
  }
  return { requiredProfiles, canApply: true, assignments, warnings: ['演示配对：3 个京东账号 + 2 个淘宝/天猫账号，可使用 3 份资料。'] };
}
export async function dispatch(request) {
  const success = data => ({ ok: true, data });
  const failure = error => ({ ok: false, error });
  const changing = ['save_shop', 'delete_shop', 'save_settings', 'apply_plan', 'open_shop'];
  if (changing.includes(request.action) && request.revision !== String(revision)) return failure('演示配置已更新，请刷新后重试。');
  if (request.action === 'get_state') return success(snapshot());
  if (request.action === 'plan_assignments') return success({ plan: plan(request.profileDirectories || profiles.map(p => p.directoryName)), revision: String(revision), planToken: `demo-${revision}` });
  if (request.action === 'save_shop') {
    const shop = structuredClone(request.shop);
    if (!shop.name.trim() || !shop.accountAlias.trim()) return failure('店铺名称与账号标识必填。');
    if (!/^https?:\/\//i.test(shop.homeUrl)) return failure('后台网址只支持 HTTP 或 HTTPS。');
    if (shop.profileDirectory && config.shops.some(item => item.id !== shop.id && item.profileDirectory === shop.profileDirectory && realm(item) === realm(shop) && item.accountAlias.trim().toLowerCase() !== shop.accountAlias.trim().toLowerCase())) return failure('该资料已绑定同一登录体系的另一个账号，请选择其他资料。');
    const index = config.shops.findIndex(item => item.id === shop.id);
    if (index >= 0) config.shops[index] = shop; else config.shops.push(shop);
  } else if (request.action === 'delete_shop') config.shops = config.shops.filter(shop => shop.id !== request.id);
  else if (request.action === 'save_settings') { config.chromeExecutable = request.chromeExecutable; config.userDataRoot = request.userDataRoot; }
  else if (request.action === 'apply_plan') {
    if (request.planToken !== `demo-${revision}`) return failure('请重新生成预览。');
    const result = plan(request.profileDirectories || profiles.map(p => p.directoryName));
    if (!result.canApply) return failure('选择的资料数量不足。');
    for (const item of result.assignments) config.shops.find(s => s.id === item.shopId).profileDirectory = item.profileDirectory;
  } else if (request.action === 'open_shop') return success({ opened: false, testOnly: true, message: '演示：将用对应资料打开后台；未启动真实 Chrome。' });
  else return failure('未知操作。');
  revision++;
  return success(snapshot());
}
