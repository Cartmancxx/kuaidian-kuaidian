// Runs the real popup module in a lightweight in-memory page/Chrome fixture.
// Never opens Chrome, registers a host, reads profiles, or calls native window APIs.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.resolve(__dirname, '../ShopController/extension/popup.js'), 'utf8')
  .replace(/^import[^\n]*\n/, '');
const clone = value => JSON.parse(JSON.stringify(value));

function node() {
  const attributes = new Map(), classes = new Set(), listeners = new Map();
  return {
    hidden: false, disabled: false, value: '', textContent: '', title: '', children: [],
    classList: {
      add(name) { classes.add(name); },
      toggle(name, enabled) { if (enabled) classes.add(name); else classes.delete(name); },
      contains(name) { return classes.has(name); },
    },
    setAttribute(name, value) { attributes.set(name, String(value)); },
    getAttribute(name) { return attributes.get(name); },
    addEventListener(name, callback) { listeners.set(name, callback); },
    async fire(name) { return listeners.get(name)?.(); },
    replaceChildren(...children) { this.children = children; },
    append(...children) { this.children.push(...children); },
  };
}

async function settle() {
  for (let index = 0; index < 6; index++) await new Promise(resolve => setImmediate(resolve));
}

async function page(options = {}) {
  const elements = new Map();
  const get = id => {
    if (!elements.has(id)) elements.set(id, node());
    return elements.get(id);
  };
  const window = node();
  window.open = () => {};
  const state = {
    pinned: options.pinned ?? false,
    native: [], requests: [], type: options.type ?? 'popup',
    capabilitiesFailure: !!options.failCapabilities,
  };
  const chrome = {
    windows: { async getCurrent() { return { id: 10, type: state.type }; } },
    runtime: {
      id: 'hadeebhijljjdebkaiaglaeipajnnind',
      async openOptionsPage() {},
      sendNativeMessage(host, message, callback) {
        state.native.push({ host, ...clone(message) });
        if (options.failNative || options.failSet && message.action === 'set_launcher_pin') {
          callback({ ok: false, error: '模拟置顶失败' });
          return;
        }
        if (message.action === 'set_launcher_pin' && !options.ignoreSet) state.pinned = message.enabled;
        callback({ ok: true, data: { pinned: state.pinned } });
      },
    },
  };
  const context = vm.createContext({
    chrome, window, URLSearchParams,
    location: { search: options.windowQuery === false ? '' : '?window=1' },
    document: { getElementById: get, body: node() },
    isDemo: !!options.demo,
    async request(action) {
      state.requests.push(action);
      if (action === 'get_capabilities') {
        if (state.capabilitiesFailure) throw new Error('Host protocol mismatch');
        return { hostVersion: '1.0.0', protocolVersion: 1,
          platform: options.platform ?? 'windows', capabilities: { pin: options.pinCapability ?? true } };
      }
      if (action !== 'get_state') throw new Error('Unexpected request: ' + action);
      return { revision: 'fixture-revision', config: { shops: [] }, profiles: [], platforms: [] };
    },
    el(tag, properties = {}, children = []) {
      const result = node();
      for (const [name, value] of Object.entries(properties)) {
        if (name === 'text') result.textContent = value;
        else result.setAttribute(name, value);
      }
      result.append(...children);
      return result;
    },
    platformLabel: (_, value) => value,
    profileLabel: (_, value) => value,
    setTimeout: () => 1, clearTimeout: () => {},
  });
  await vm.runInContext(`(async () => {\n${source}\n})()`, context, { filename: 'popup.js' });
  await settle();
  return { state, get, window };
}

const tests = [];
const test = (name, body) => tests.push({ name, body });

test('a newly opened real popup requests topmost and confirms the result', async () => {
  const fixture = await page();
  assert.deepEqual(fixture.state.native.map(item => item.action), ['get_launcher_pin', 'set_launcher_pin']);
  assert.equal(fixture.state.native[1].enabled, true);
  assert.ok(fixture.state.native.every(item => item.host === 'com.shopcontroller.chrome'));
  assert.equal(fixture.get('pin').getAttribute('aria-pressed'), 'true');
  assert.equal(fixture.get('pin').classList.contains('active'), true);
});

test('an already pinned window does not receive a redundant set operation', async () => {
  const fixture = await page({ pinned: true });
  assert.deepEqual(fixture.state.native.map(item => item.action), ['get_launcher_pin']);
  assert.equal(fixture.get('pin').getAttribute('aria-pressed'), 'true');
});

test('ordinary browser windows never receive native pin operations', async () => {
  const fixture = await page({ type: 'normal' });
  assert.equal(fixture.state.native.length, 0);
  assert.equal(fixture.get('pin').hidden, true);
});

test('Mac popup retains its launcher but never requests Windows pinning', async () => {
  const fixture = await page({ platform: 'macos', pinCapability: false });
  assert.equal(fixture.state.native.length, 0);
  assert.equal(fixture.get('pin').hidden, true);
  assert.ok(fixture.state.requests.includes('get_state'));
});

test('Mac platform remains unpinned even if a malformed capability claims pin support', async () => {
  const fixture = await page({ platform: 'macos', pinCapability: true });
  assert.equal(fixture.state.native.length, 0);
  assert.equal(fixture.get('pin').hidden, true);
});

test('a disabled capability or failed handshake never reaches native pin operations', async () => {
  for (const options of [{ pinCapability: false }, { failCapabilities: true }]) {
    const fixture = await page(options);
    assert.equal(fixture.state.native.length, 0);
    assert.equal(fixture.get('pin').hidden, true);
  }
});

test('non-window popup content never auto-pins a browser window', async () => {
  const fixture = await page({ windowQuery: false });
  assert.equal(fixture.state.native.length, 0);
  assert.equal(fixture.get('pin').hidden, true);
});

test('a native connection failure never displays confirmed topmost state', async () => {
  const fixture = await page({ failNative: true });
  assert.notEqual(fixture.get('pin').getAttribute('aria-pressed'), 'true');
  assert.equal(fixture.get('pin').classList.contains('active'), false);
  assert.equal(fixture.state.native.filter(item => item.action === 'set_launcher_pin').length, 0);
});

test('a failed native set never displays confirmed topmost state', async () => {
  const fixture = await page({ failSet: true });
  assert.notEqual(fixture.get('pin').getAttribute('aria-pressed'), 'true');
  assert.equal(fixture.get('pin').classList.contains('active'), false);
  assert.equal(fixture.state.pinned, false);
});

test('a successful reply with an unchanged false state is not treated as pinned', async () => {
  const fixture = await page({ ignoreSet: true });
  assert.notEqual(fixture.get('pin').getAttribute('aria-pressed'), 'true');
  assert.equal(fixture.get('pin').classList.contains('active'), false);
});

test('manual unpin is respected when focus returns', async () => {
  const fixture = await page();
  await fixture.get('pin').fire('click');
  await settle();
  assert.equal(fixture.state.pinned, false);
  assert.equal(fixture.get('pin').getAttribute('aria-pressed'), 'false');
  const before = fixture.state.native.length;
  await fixture.window.fire('focus');
  await settle();
  assert.deepEqual(fixture.state.native.slice(before).map(item => item.action), ['get_launcher_pin']);
  assert.equal(fixture.get('pin').getAttribute('aria-pressed'), 'false');
});

test('demo mode simulates default pinning without native calls', async () => {
  const fixture = await page({ demo: true });
  assert.equal(fixture.state.native.length, 0);
  assert.equal(fixture.get('pin').getAttribute('aria-pressed'), 'true');
  assert.match(fixture.get('pin').title, /演示/);
  await fixture.get('pin').fire('click');
  assert.equal(fixture.get('pin').getAttribute('aria-pressed'), 'false');
  assert.equal(fixture.state.native.length, 0);
});

test('a helper connected after the window opened can restore pin support without reopening the window', async () => {
  const fixture = await page({ failCapabilities: true });
  assert.equal(fixture.get('pin').hidden, true);
  assert.equal(fixture.state.native.length, 0);
  fixture.state.capabilitiesFailure = false;
  await fixture.window.fire('focus');
  await settle();
  assert.equal(fixture.get('pin').hidden, false);
  assert.equal(fixture.get('pin').getAttribute('aria-pressed'), 'true');
  assert.deepEqual(fixture.state.native.map(item => item.action), ['get_launcher_pin', 'set_launcher_pin']);
});

(async () => {
  let passed = 0;
  for (const item of tests) {
    try { await item.body(); passed++; console.log('PASS ', item.name); }
    catch (error) { console.error('FAIL ', item.name, error); }
  }
  console.log(`\n${passed}/${tests.length} default pin checks passed. All DOM and native APIs were mocked.`);
  if (passed !== tests.length) process.exitCode = 1;
})();
