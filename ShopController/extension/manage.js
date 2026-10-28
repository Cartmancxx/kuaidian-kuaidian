import { request, isDemo, element as el, profileLabel, platformLabel } from './api.js';
const $ = id => document.getElementById(id);
let state = null;
let filter = 'all';
let planData = null;
let planPool = [];
let planSequence = 0;
let toastTimer;
let loadingSequence = 0;
let mutationPending = false;
let shopFormRevision = '';
let settingsFormRevision = '';

function toast(text, error = false) {
  clearTimeout(toastTimer);
  $('toast').textContent = text;
  $('toast').classList.toggle('error', error);
  $('toast').hidden = false;
  toastTimer = setTimeout(() => { $('toast').hidden = true; }, 6500);
}
function showFormError(id, message) { $(id).textContent = message; $(id).hidden = !message; }
function render() {
  $('add-shop').disabled = false;
  $('plan-button').disabled = state.config.shops.length === 0;
  $('shop-count').textContent = `${state.config.shops.length} 个店铺入口`;
  $('profile-count').textContent = `${state.profiles.length} 份资料`;
  $('connection-state').textContent = isDemo ? '演示数据 · 未连接真实账号' : `助手 ${state.hostVersion} · ${state.platform === 'macos' ? 'macOS' : 'Windows'} · 未检测登录状态`;
  const warningList = [...state.warnings];
  if (!state.profiles.length) warningList.push('尚未发现 Chrome 资料。请先在 Chrome 中创建并打开资料，再点击“刷新资料”。');
  $('warnings').hidden = !warningList.length;
  $('warnings').replaceChildren(...warningList.map(text => el('p', { text })));
  renderShops();
  const groups = new Map();
  for (const shop of state.config.shops) {
    if (!shop.profileDirectory) continue;
    const group = groups.get(shop.profileDirectory) || [];
    group.push(shop);
    groups.set(shop.profileDirectory, group);
  }
  $('profile-list').replaceChildren(...[...groups.entries()].map(([directory, shops]) => el('section', { class: 'profile-row' }, [
    el('h3', { text: profileLabel(state, directory) }),
    ...shops.map(shop => el('p', { text: `${platformLabel(state, shop.platform)} · ${shop.name}` }))
  ])));
  if (!groups.size) $('profile-list').append(el('p', { class: 'panel-description', text: '添加店铺并绑定资料后，这里会显示每份资料对应的店铺。' }));
}
function renderShops() {
  if (!state) return;
  const term = $('search').value.trim().toLocaleLowerCase();
  const visible = state.config.shops.filter(shop =>
    (filter === 'all' || shop.platform === filter || filter === 'alibaba' && ['Taobao', 'Tmall'].includes(shop.platform)) &&
    `${shop.name} ${shop.accountAlias} ${shop.notes}`.toLocaleLowerCase().includes(term));
  const cards = visible.map(shop => {
    const open = el('button', { type: 'button', class: 'button primary small', text: shop.profileDirectory ? '打开后台' : '绑定资料', 'aria-label': `打开 ${shop.name} 后台` });
    open.addEventListener('click', () => shop.profileDirectory ? openShop(shop, open) : editShop(shop));
    const edit = el('button', { type: 'button', class: 'button small', text: '编辑', 'aria-label': `编辑 ${shop.name}`, onclick: () => editShop(shop) });
    return el('article', { class: 'shop-card' }, [
      el('div', { class: 'card-top' }, [el('span', { class: `platform ${shop.platform}`, text: platformLabel(state, shop.platform) }), el('span', { class: 'profile-badge', text: profileLabel(state, shop.profileDirectory), title: profileLabel(state, shop.profileDirectory) })]),
      el('h3', { text: shop.name }),
      el('p', { class: 'account-label', text: `账号标识：${shop.accountAlias}` }),
      el('p', { class: 'shop-notes', text: shop.notes || '登录状态以平台页面为准' }),
      el('div', { class: 'card-bottom' }, [open, edit])
    ]);
  });
  $('shop-list').replaceChildren(...cards);
  $('empty-state').hidden = state.config.shops.length !== 0;
  if (!cards.length && state.config.shops.length) $('shop-list').append(el('p', { class: 'empty-filter', text: '没有匹配的店铺，试试其他关键词。' }));
}
async function loadState() {
  const sequence = ++loadingSequence;
  $('refresh').disabled = true;
  try {
    const received = await request('get_state');
    if (sequence !== loadingSequence) return;
    state = received;
    $('connection-error').hidden = true;
    render();
  } catch (error) {
    if (sequence !== loadingSequence) return;
    $('connection-error-text').textContent = error.message;
    $('connection-error').hidden = false;
    $('connection-state').textContent = '连接待检查';
    $('add-shop').disabled = true;
    $('plan-button').disabled = true;
  } finally { if (sequence === loadingSequence) $('refresh').disabled = false; }
}
async function openShop(shop, button) {
  if (mutationPending) return;
  mutationPending = true;
  button.disabled = true;
  try {
    const reply = await request('open_shop', { id: shop.id, revision: state.revision });
    toast(reply.warning || reply.message || '演示：已选择对应资料，未启动真实 Chrome。');
    await loadState();
  } catch (error) { toast(error.message, true); }
  finally { mutationPending = false; button.disabled = false; }
}
function editShop(shop = null) {
  if (!state) return;
  shopFormRevision = state.revision;
  const form = $('shop-form');
  form.reset();
  $('shop-dialog-title').textContent = shop ? '编辑店铺' : '添加店铺';
  form.elements.platform.replaceChildren(...state.platforms.map(p => el('option', { value: p.value, text: p.label })));
  form.elements.profileDirectory.replaceChildren(el('option', { value: '', text: '暂不绑定，稍后统一配对' }), ...state.profiles.map(p => el('option', { value: p.directoryName, text: `${p.displayName} · ${p.directoryName}` })));
  for (const field of ['id', 'name', 'platform', 'accountAlias', 'profileDirectory', 'homeUrl', 'notes']) {
    form.elements[field].value = shop?.[field] ?? (field === 'platform' ? 'JD' : '');
  }
  if (shop?.profileDirectory && !state.profiles.some(p => p.directoryName === shop.profileDirectory)) {
    form.elements.profileDirectory.append(el('option', { value: shop.profileDirectory, text: `${shop.profileDirectory}（已不存在，请重新选择）` }));
    form.elements.profileDirectory.value = shop.profileDirectory;
  }
  if (!shop) form.elements.homeUrl.value = state.platforms.find(p => p.value === 'JD')?.defaultUrl || '';
  $('delete-shop').hidden = !shop;
  showFormError('shop-error', '');
  $('shop-dialog').showModal();
}
async function saveShop(event) {
  event.preventDefault();
  if (mutationPending) return;
  mutationPending = true;
  $('save-shop').disabled = true;
  const form = $('shop-form');
  const shop = Object.fromEntries(new FormData(form));
  shop.id ||= crypto.randomUUID();
  try {
    state = await request('save_shop', { shop, revision: shopFormRevision });
    render();
    $('shop-dialog').close();
    toast('店铺入口已保存。打开后台后请核对实际登录账号。');
  } catch (error) { showFormError('shop-error', error.message); }
  finally { mutationPending = false; $('save-shop').disabled = false; }
}
function openPlan() {
  ++planSequence;
  planData = null;
  $('recalculate-plan').disabled = false;
  $('apply-plan').disabled = true;
  $('plan-summary').textContent = '先选择可用于电商的 Chrome 资料';
  $('plan-rows').replaceChildren();
  $('plan-warnings').textContent = '配对只修改入口绑定，不会把旧资料中的登录状态迁移到新资料。';
  const bound = new Set(state.config.shops.map(s => s.profileDirectory));
  $('profile-pool').replaceChildren(...state.profiles.map(profile => {
    const checkbox = el('input', { type: 'checkbox', value: profile.directoryName });
    checkbox.checked = bound.has(profile.directoryName);
    checkbox.addEventListener('change', () => { ++planSequence; planData = null; $('recalculate-plan').disabled = false; $('apply-plan').disabled = true; $('plan-summary').textContent = '资料选择已变化，请重新生成预览'; });
    return el('label', { class: 'pool-option' }, [checkbox, el('span', { text: `${profile.displayName} · ${profile.directoryName}` })]);
  }));
  $('plan-dialog').showModal();
}
async function calculatePlan() {
  const sequence = ++planSequence;
  $('recalculate-plan').disabled = true;
  $('apply-plan').disabled = true;
  planData = null;
  try {
    const selectedPool = [...$('profile-pool').querySelectorAll('input:checked')].map(node => node.value);
    const reply = await request('plan_assignments', { profileDirectories: selectedPool });
    if (sequence !== planSequence) return;
    if (reply.revision !== state.revision) {
      await loadState();
      throw new Error('店铺配置已在其他窗口更新，列表已刷新。请关闭配对窗口后重新预览。');
    }
    planPool = selectedPool;
    const plan = reply.plan;
    planData = reply;
    $('plan-summary').textContent = `${state.config.shops.length} 个店铺入口，按已登记账号至少需要 ${plan.requiredProfiles} 份资料；本次选择 ${planPool.length} 份。`;
    $('plan-rows').replaceChildren(...plan.assignments.map(assignment => {
      const shop = state.config.shops.find(s => s.id === assignment.shopId);
      const changed = shop.profileDirectory !== assignment.profileDirectory;
      return el('section', { class: 'plan-row' }, [el('h3', { text: `${platformLabel(state, shop.platform)} · ${shop.name}` }), el('p', { class: changed ? 'plan-change' : '', text: changed ? `${profileLabel(state, shop.profileDirectory)} → ${profileLabel(state, assignment.profileDirectory)}` : `${profileLabel(state, assignment.profileDirectory)} · 保持绑定` })]);
    }));
    $('plan-warnings').replaceChildren(...[...plan.warnings, '未登记在控制器中的账号不参与冲突判断，请确认所选资料可用于这些店铺。'].map(text => el('p', { text })));
    $('apply-plan').disabled = !plan.canApply;
  } catch (error) { if (sequence === planSequence) { planData = null; $('plan-warnings').textContent = error.message; } }
  finally { if (sequence === planSequence) $('recalculate-plan').disabled = false; }
}
async function applyPlan() {
  if (!planData || mutationPending) return;
  mutationPending = true;
  $('apply-plan').disabled = true;
  try {
    state = await request('apply_plan', { revision: planData.revision, planToken: planData.planToken, profileDirectories: planPool });
    render();
    $('plan-dialog').close();
    toast('入口绑定已更新。首次打开调整过的店铺，请检查账号并按需重新登录。');
  } catch (error) { $('plan-warnings').textContent = error.message; planData = null; }
  finally { mutationPending = false; }
}
function openSettings() {
  if (!state) { $('connection-error').hidden = false; return; }
  settingsFormRevision = state.revision;
  const form = $('settings-form');
  form.elements.chromeExecutable.value = state.config.chromeExecutable;
  form.elements.userDataRoot.value = state.config.userDataRoot;
  form.elements.chromeExecutable.placeholder = state.platform === 'macos' ? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' : 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
  form.elements.userDataRoot.placeholder = state.platform === 'macos' ? '~/Library/Application Support/Google/Chrome（填写完整路径）' : '…\\Google\\Chrome\\User Data';
  $('detected-settings').replaceChildren(el('p', { text: `当前程序：${state.chromeExecutable || '未检测到'}` }), el('p', { text: `当前资料根目录：${state.userDataRoot}` }));
  showFormError('settings-error', '');
  $('settings-dialog').showModal();
}
$('shop-form').addEventListener('submit', saveShop);
$('shop-form').elements.platform.addEventListener('change', () => {
  const form = $('shop-form');
  if (!form.elements.homeUrl.value || state.platforms.some(p => p.defaultUrl && p.defaultUrl === form.elements.homeUrl.value))
    form.elements.homeUrl.value = state.platforms.find(p => p.value === form.elements.platform.value)?.defaultUrl || '';
});
$('delete-shop').addEventListener('click', async () => {
  if (mutationPending || !confirm('仅删除控制器中的这个入口？Chrome 资料、Cookie 和账号不受影响。')) return;
  mutationPending = true;
  try {
    state = await request('delete_shop', { id: $('shop-form').elements.id.value, revision: shopFormRevision });
    render(); $('shop-dialog').close(); toast('入口已删除，Chrome 资料保持原样。');
  } catch (error) { showFormError('shop-error', error.message); }
  finally { mutationPending = false; }
});
$('settings-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (mutationPending) return;
  mutationPending = true;
  try {
    state = await request('save_settings', { ...Object.fromEntries(new FormData(event.currentTarget)), revision: settingsFormRevision });
    render(); $('settings-dialog').close(); toast('连接设置已保存。');
  } catch (error) { showFormError('settings-error', error.message); }
  finally { mutationPending = false; }
});
document.querySelectorAll('[data-close]').forEach(button => button.addEventListener('click', () => $(button.dataset.close).close()));
document.querySelectorAll('[data-filter]').forEach(button => button.addEventListener('click', () => {
  filter = button.dataset.filter;
  document.querySelectorAll('[data-filter]').forEach(item => { const active = item === button; item.classList.toggle('active', active); item.setAttribute('aria-pressed', String(active)); });
  renderShops();
}));
$('add-shop').addEventListener('click', () => editShop());
$('empty-add').addEventListener('click', () => editShop());
$('search').addEventListener('input', renderShops);
$('refresh').addEventListener('click', loadState);
$('retry').addEventListener('click', loadState);
$('settings-button').addEventListener('click', openSettings);
$('plan-button').addEventListener('click', openPlan);
$('recalculate-plan').addEventListener('click', calculatePlan);
$('apply-plan').addEventListener('click', applyPlan);
$('demo-banner').hidden = !isDemo;
loadState();
