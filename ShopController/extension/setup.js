import { request, isDemo } from './api.js';
const $ = id => document.getElementById(id);
function httpsLink(value) {
  try { const url = new URL(value); return url.protocol === 'https:' && !url.username && !url.password ? url.href : null; }
  catch { return null; }
}
try {
  const info = await fetch('./release-info.json').then(result => result.json());
  const download = httpsLink(info.downloadPageUrl);
  $('download-pending').hidden = !!download;
  $('download').hidden = !download;
  if (download) $('download').href = download;
} catch { $('download-pending').hidden = false; }
let os = '';
try { os = (await chrome.runtime.getPlatformInfo()).os; } catch { /* A local preview has no Chrome runtime. */ }
$('platform-instruction').textContent = os === 'mac' ? '你正在使用 macOS。选择 Apple 芯片或 Intel 版助手，按安装说明完成登记；此版本的 Mac 小窗不置顶。' : os === 'win' ? '你正在使用 Windows。下载 Windows x64 版助手，解压后运行安装入口；通常无需管理员权限。' : '提供 Windows x64、Mac Apple 芯片和 Mac Intel 安装包；请选择与你电脑匹配的版本。';
const extensionId = globalThis.chrome?.runtime?.id;
if (extensionId) { $('extension-id').textContent = extensionId; $('copy-id').disabled = false; }
$('copy-id').addEventListener('click', async () => {
  try { await navigator.clipboard.writeText(extensionId); $('copy-status').textContent = '已复制扩展 ID。'; }
  catch { $('copy-status').textContent = '请选中上方 ID 后复制。'; }
});
async function check() {
  $('check').disabled = true;
  $('connection-title').textContent = '正在检查连接…';
  try {
    const result = await request('get_capabilities');
    $('connection-title').textContent = isDemo ? '演示连接状态' : '本地助手已连接';
    const windowMode = result.platform === 'windows' && result.capabilities.pin ? '支持置顶' : '普通独立小窗';
    $('connection-detail').textContent = `${isDemo ? '示例数据 · ' : ''}助手 ${result.hostVersion} · ${result.platform === 'macos' ? 'macOS' : 'Windows'} · ${windowMode} · 通信正常不代表店铺已登录`;
    $('connection-dot').className = 'state-dot connected';
  } catch (error) {
    $('connection-title').textContent = '等待连接本地助手';
    $('connection-detail').textContent = error.message;
    $('connection-dot').className = 'state-dot error';
  } finally { $('check').disabled = false; }
}
$('check').addEventListener('click', check);
await check();
