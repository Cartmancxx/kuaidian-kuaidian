// Development-only adapter served by preview_server.py; never packaged in the extension.
export const isDemo = true;
export const protocolVersion = 1;
import { dispatch } from './demo.js';
export async function getCapabilities() {
  const platform = new URLSearchParams(location.search).get('platform') === 'macos' ? 'macos' : 'windows';
  return { hostVersion: '1.0.0', protocolVersion: 1, platform, capabilities: { pin: platform === 'windows' } };
}
export async function request(action, parameters = {}) {
  if (action === 'get_capabilities') return getCapabilities();
  const result = await dispatch({ action, ...parameters });
  if (!result.ok) throw new Error(result.error);
  if (action === 'get_state' || ['save_shop','save_settings','delete_shop','apply_plan'].includes(action))
    Object.assign(result.data, await getCapabilities());
  return result.data;
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
