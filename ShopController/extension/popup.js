import { request, isDemo, element as el, profileLabel, platformLabel } from './api.js';

let state;
let busy = false;
let refreshSequence = 0;
let statusTimer;
let connectionProblem = false;
const status = document.getElementById('status');
const list = document.getElementById('stores');
const search = document.getElementById('search');
const refresh = document.getElementById('refresh');
const pin = document.getElementById('pin');
const connectLink = document.getElementById('connect-link');
const isWindow = new URLSearchParams(location.search).get('window') === '1';
let pinned;
let pinBusy = false;
let pinInitialized = false;
let demoPinned = false;
let canPin = false;
const groups = [
  { label: '京东', platforms: ['JD'], color: 'jd' },
  { label: '淘宝 / 天猫', platforms: ['Taobao', 'Tmall'], color: 'alibaba' },
  { label: 'PDD', platforms: ['Pdd'], color: 'pdd' },
  { label: '其他', platforms: ['Other'], color: 'other' }
];

if (isWindow) document.body.classList.add('is-window');
pin.hidden = true;
document.getElementById('demo-label').hidden = !isDemo;

function renderPin() {
  pin.hidden = !canPin;
  const label = pinned === undefined ? '切换置顶（状态待确认）' : pinned ? '取消置顶' : '置顶小窗';
  pin.title = isDemo ? `${label} · 演示` : label;
  pin.setAttribute('aria-label', pin.title);
  pin.setAttribute('aria-pressed', pinned === undefined ? 'mixed' : String(pinned));
  pin.classList.toggle('active', pinned === true);
  pin.disabled = pinBusy || !pinInitialized;
}

async function pinRequest(action, enabled) {
  if (isDemo) {
    if (action === 'set_launcher_pin') demoPinned = enabled;
    return { pinned: demoPinned };
  }
  if (!globalThis.chrome?.runtime?.id) throw new Error('请在 Chrome 扩展的小窗中操作置顶');
  if ((await chrome.windows.getCurrent()).type !== 'popup') {
    canPin = false;
    throw new Error('置顶仅用于独立店铺小窗，不修改普通浏览器窗口');
  }
  // Send from this page, not the service worker: Chrome supplies this window's HWND.
  const reply = await new Promise((resolve, reject) => {
    chrome.runtime.sendNativeMessage('com.shopcontroller.chrome', { action, ...(enabled === undefined ? {} : { enabled }) }, result => {
      const error = chrome.runtime.lastError;
      if (error) reject(new Error('置顶助手未连接，请检查本地助手安装'));
      else resolve(result);
    });
  });
  if (!reply?.ok || typeof reply.data?.pinned !== 'boolean') throw new Error(reply?.error || '置顶状态未确认，请重试');
  return reply.data;
}

async function refreshPin() {
  if (!canPin || !pinInitialized || pinBusy) return;
  pinBusy = true;
  renderPin();
  try { pinned = (await pinRequest('get_launcher_pin')).pinned; }
  catch { pinned = undefined; } // Initial/focus reads must not replace connection feedback.
  finally { pinBusy = false; renderPin(); }
}

async function initializePin() {
  if (!canPin || pinInitialized || pinBusy) return;
  pinBusy = true;
  renderPin();
  try {
    const current = await pinRequest('get_launcher_pin');
    pinned = current.pinned ? true : (await pinRequest('set_launcher_pin', true)).pinned;
    if (!pinned) throw new Error('系统尚未确认置顶，请点击图钉重试');
  } catch (error) {
    pinned = undefined;
    showStatus(`默认置顶未成功：${error.message}`, true);
  } finally { pinInitialized = true; pinBusy = false; renderPin(); }
}

pin.addEventListener('click', async () => {
  if (!canPin || !pinInitialized || pinBusy) return;
  pinBusy = true;
  renderPin();
  try {
    // Re-read before toggling, so another window or OS action cannot leave a stale toggle.
    const current = await pinRequest('get_launcher_pin');
    const desired = !current.pinned;
    pinned = (await pinRequest('set_launcher_pin', desired)).pinned;
    if (pinned !== desired) throw new Error('窗口置顶状态未改变，请重试');
    showStatus(isDemo ? `演示：${pinned ? '已置顶' : '已取消置顶'}，不改变真实窗口` : pinned ? '小窗已置顶' : '已取消置顶');
  } catch (error) {
    pinned = undefined;
    showStatus(error.message, true);
  } finally { pinBusy = false; renderPin(); }
});

function showStatus(message, error = false) {
  clearTimeout(statusTimer);
  status.textContent = message;
  status.hidden = !message;
  status.classList.toggle('error', error);
  if (message && !error) statusTimer = setTimeout(() => { status.hidden = true; }, 4500);
}

function render() {
  if (!state) return;
  // Keep the displayed record and its revision together across asynchronous refreshes.
  const snapshot = state;
  const query = search.value.trim().toLocaleLowerCase();
  const shops = snapshot.config.shops.filter(shop =>
    `${shop.name} ${shop.accountAlias} ${platformLabel(snapshot, shop.platform)}`.toLocaleLowerCase().includes(query));
  const sections = groups.map(group => {
    const matching = shops.filter(shop => group.platforms.includes(shop.platform));
    if (!matching.length) return null;
    return el('section', { class: `platform-group ${group.color}`, 'aria-label': group.label }, [
      el('h2', { class: 'group-heading', text: group.label }),
      ...matching.map(shop => {
        const profile = profileLabel(snapshot, shop.profileDirectory);
        const button = el('button', {
          class: 'store-row', type: 'button', 'aria-label': `打开 ${shop.name}`,
          title: `${shop.name} · ${platformLabel(snapshot, shop.platform)} · ${profile}\n账号标识：${shop.accountAlias}`
        }, [
          el('span', { class: 'platform-dot', 'aria-hidden': 'true' }),
          el('span', { class: 'store-name', text: shop.name }),
          el('span', { class: `store-profile${shop.profileDirectory ? '' : ' unbound'}`, text: profile })
        ]);
        button.disabled = busy;
        button.addEventListener('click', () => openShop(shop, snapshot.revision));
        return button;
      })
    ]);
  }).filter(Boolean);
  list.replaceChildren(...sections);
  if (!sections.length) list.append(el('p', { class: 'empty-state', text: snapshot.config.shops.length ? '没有找到这家店铺' : '暂无店铺，点右上角“管理”添加' }));
}

async function loadState({ silent = false } = {}) {
  const sequence = ++refreshSequence;
  refresh.disabled = true;
  try {
    const received = await request('get_state');
    if (sequence !== refreshSequence) return;
    state = received;
    connectLink.hidden = true;
    render();
    if (!silent || connectionProblem) showStatus('');
    connectionProblem = false;
  } catch (error) {
    if (sequence !== refreshSequence) return;
    connectionProblem = true;
    connectLink.hidden = false;
    if (!state) list.replaceChildren(el('p', { class: 'empty-state', text: '连接本地助手后，店铺会显示在这里' }));
    showStatus(error.message, true);
  } finally {
    if (sequence === refreshSequence) refresh.disabled = false;
  }
}

async function openShop(shop, revision) {
  if (busy) return;
  if (!shop.profileDirectory) { showStatus('先在“管理”中为这家店绑定资料', true); return; }
  busy = true;
  ++refreshSequence; // Discard any refresh started before this click.
  render();
  try {
    const result = await request('open_shop', { id: shop.id, revision });
    showStatus(result.warning || (isDemo ? `演示：打开 ${shop.name}，未启动 Chrome` : `已请求打开 ${shop.name}，请核对网页账号`), !!result.warning);
  } catch (error) {
    showStatus(error.message, true);
  } finally {
    await loadState({ silent: true });
    busy = false;
    render();
  }
}

document.getElementById('manage').addEventListener('click', async () => {
  if (isDemo) window.open('manage.html?demo=1', '_blank', 'noopener');
  else if (globalThis.chrome?.runtime?.id) {
    try { await chrome.runtime.openOptionsPage(); }
    catch { showStatus('管理页面打开失败，请从扩展菜单重试', true); }
  } else window.open('help.html', '_blank', 'noopener');
});
search.addEventListener('input', render);
async function detectPinSupport() {
  try {
    const info = await request('get_capabilities');
    canPin = isWindow && info.platform === 'windows' && info.capabilities.pin === true &&
      (isDemo || !!globalThis.chrome?.runtime?.id && (await chrome.windows.getCurrent()).type === 'popup');
  } catch { canPin = false; }
  renderPin();
}
async function refreshView(options) {
  if (busy) return;
  // The helper may have been installed while this window remained open.
  if (!pinInitialized && !canPin) await detectPinSupport();
  await loadState(options);
  if (!pinInitialized) await initializePin();
  else await refreshPin();
}
refresh.addEventListener('click', () => refreshView());
window.addEventListener('focus', () => refreshView({ silent: true }));
await detectPinSupport();
renderPin();
await loadState();
// Apply once when the small window opens. Focus changes only read the state,
// so manually unpinning this window remains respected while it stays open.
await initializePin();
