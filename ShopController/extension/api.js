// Store builds have no sample-data mode. Local previews use a separate server adapter.
export const isDemo = false;
export const protocolVersion = 1;
let handshake;
async function send(action, parameters = {}) {
  if (!globalThis.chrome?.runtime?.id) throw new Error('请从 Chrome 工具栏打开已安装的快店快点。');
  const reply = await chrome.runtime.sendMessage({ action, ...parameters });
  if (!reply?.ok) {
    if (reply?.connectionError) handshake = null;
    const error = new Error(reply?.error || '本地助手未返回有效结果。');
    error.connectionError = !!reply?.connectionError;
    throw error;
  }
  return reply.data;
}
function checkCapabilities(data) {
  if (data?.protocolVersion !== protocolVersion || typeof data?.hostVersion !== 'string' ||
      typeof data?.capabilities?.pin !== 'boolean') {
    const error = new Error('本地助手与扩展版本不匹配，请在“连接助手”页更新助手后重试。');
    error.connectionError = true;
    throw error;
  }
  if (!['windows', 'macos'].includes(data.platform)) throw new Error('当前版本支持 Windows 和 macOS 上的 Google Chrome。');
  return data;
}
export async function getCapabilities({ refresh = false } = {}) {
  if (refresh) handshake = null;
  handshake ||= send('get_capabilities').then(checkCapabilities).catch(error => { handshake = null; throw error; });
  return handshake;
}
export async function request(action, parameters = {}) {
  if (action === 'get_capabilities') return getCapabilities({ refresh: true });
  await getCapabilities();
  return send(action, parameters);
}
export function element(tag, properties = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(properties)) {
    if (key === 'text') node.textContent = value;
    else if (key === 'class') node.className = value;
    else if (key.startsWith('on')) node.addEventListener(key.slice(2).toLowerCase(), value);
    else node.setAttribute(key, value);
  }
  node.append(...children);
  return node;
}
export function profileLabel(state, directory) {
  return state.profiles.find(profile => profile.directoryName === directory)?.displayName || (directory ? `${directory}（待检查）` : '待绑定资料');
}
export function platformLabel(state, platform) {
  return state.platforms.find(item => item.value === platform)?.label || platform;
}

