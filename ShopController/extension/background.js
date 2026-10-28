const allowedActions = new Set(['get_capabilities', 'get_state', 'save_shop', 'delete_shop', 'plan_assignments', 'apply_plan', 'open_shop', 'save_settings']);
const launcherWindowKey = 'launcherWindowId';
let openingLauncher = null;

// A real Chrome popup window stays open after losing focus. This is deliberately
// not action.default_popup, which disappears as soon as a shop gets focus.
async function openLauncherWindow() {
  const saved = await chrome.storage.session.get(launcherWindowKey);
  if (Number.isInteger(saved[launcherWindowKey])) {
    try {
      const existing = await chrome.windows.get(saved[launcherWindowKey]);
      if (existing.type === 'popup') {
        await chrome.windows.update(existing.id, { focused: true, ...(existing.state === 'minimized' ? { state: 'normal' } : {}) });
        return;
      }
    } catch { /* A previously closed window should be recreated. */ }
    await chrome.storage.session.remove(launcherWindowKey);
  }
  const created = await chrome.windows.create({
    url: chrome.runtime.getURL('popup.html?window=1'), type: 'popup', width: 320, height: 390, focused: true
  });
  if (Number.isInteger(created?.id)) await chrome.storage.session.set({ [launcherWindowKey]: created.id });
}
chrome.action.onClicked.addListener(() => {
  if (openingLauncher) return;
  openingLauncher = openLauncherWindow().then(async () => {
    await chrome.action.setBadgeText({ text: '' });
    await chrome.action.setTitle({ title: '打开快店快点' });
  }).catch(error => {
    console.error('店铺小窗打开失败：', error.message);
    chrome.action.setBadgeText({ text: '!' });
    chrome.action.setTitle({ title: '小窗打开失败，请重新点击' });
  }).finally(() => { openingLauncher = null; });
});
// Keep the ID until the next open. Validating windows.get avoids a close/create
// race that could otherwise delete a newer window's session ID.
chrome.runtime.onMessage.addListener((message, sender, respond) => {
  const allowedPages = ['manage.html', 'popup.html', 'setup.html'].map(path => chrome.runtime.getURL(path));
  const senderPage = (sender.url || '').split('?')[0].split('#')[0];
  if (sender.id !== chrome.runtime.id || !allowedPages.includes(senderPage) || !allowedActions.has(message?.action)) {
    respond({ ok: false, error: '请求来源或操作无效。' });
    return false;
  }
  chrome.runtime.sendNativeMessage('com.shopcontroller.chrome', message, result => {
    const error = chrome.runtime.lastError;
    respond(error ? { ok: false, error: '本地助手尚未连接，请打开“连接助手”页完成安装或更新。', connectionError: true } : result);
  });
  return true;
});
