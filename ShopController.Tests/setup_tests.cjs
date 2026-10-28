// Runs the real onboarding module with mock DOM, local metadata, and capability replies.
// Does not fetch a URL, copy to a real clipboard, or contact an installed native host.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.resolve(__dirname, '../ShopController/extension/setup.js'), 'utf8')
  .replace(/^import[^\n]*\n/, '');

async function page(options = {}) {
  const nodes = new Map(), calls = [], copied = [];
  function get(id) {
    if (!nodes.has(id)) nodes.set(id, {
      hidden: false, disabled: id === 'copy-id', textContent: '', href: '', className: '', listeners: new Map(),
      addEventListener(type, callback) { this.listeners.set(type, callback); },
      async fire(type) { return this.listeners.get(type)?.(); },
    });
    return nodes.get(id);
  }
  const id = 'abcdefghijklmnopabcdefghijklmnop';
  let failure = !!options.failure;
  const context = vm.createContext({
    URL, isDemo: false, document: { getElementById: get },
    chrome: options.noRuntime ? undefined : { runtime: { id, async getPlatformInfo() { return { os: options.os ?? 'win' }; } } },
    navigator: { clipboard: { async writeText(value) { if (options.clipboardFailure) throw new Error('Not permitted'); copied.push(value); } } },
    async fetch(url) {
      calls.push(['fetch', url]);
      assert.equal(url, './release-info.json');
      if (options.metadataFailure) throw new Error('Missing local metadata');
      return { async json() { return { downloadPageUrl: options.download ?? '' }; } };
    },
    async request(action) {
      calls.push(['request', action]);
      assert.equal(action, 'get_capabilities');
      if (failure) throw new Error('Fixture connection failure');
      return { hostVersion: '1.0.0', protocolVersion: 1, platform: options.os === 'mac' ? 'macos' : 'windows', capabilities: { pin: options.pinCapability ?? options.os !== 'mac' } };
    },
  });
  await vm.runInContext(`(async () => {\n${source}\n})()`, context, { filename: 'setup.js' });
  return { get, calls, copied, id, reconnect() { failure = false; return get('check').fire('click'); } };
}

const tests = [];
const test = (name, body) => tests.push({ name, body });

test('an unset public download URL displays an honest pending state', async () => {
  const app = await page();
  assert.equal(app.get('download').hidden, true);
  assert.equal(app.get('download-pending').hidden, false);
  assert.equal(app.get('download').href, '');
  assert.deepEqual(app.calls, [['fetch', './release-info.json'], ['request', 'get_capabilities']]);
});

test('only credential-free HTTPS downloads are offered', async () => {
  const valid = await page({ download: 'https://example.invalid/download' });
  assert.equal(valid.get('download').href, 'https://example.invalid/download');
  assert.equal(valid.get('download').hidden, false);
  assert.equal(valid.get('download-pending').hidden, true);
  for (const download of ['javascript:alert(1)', 'http://example.invalid', 'https://user:secret@example.invalid', 'file:///tmp/helper', '']) {
    const app = await page({ download });
    assert.equal(app.get('download').hidden, true, download);
    assert.equal(app.get('download').href, '', download);
  }
});

test('Mac onboarding describes a normal small window and never requests native pinning', async () => {
  const app = await page({ os: 'mac' });
  assert.match(app.get('platform-instruction').textContent, /Mac 小窗不置顶/);
  assert.match(app.get('connection-detail').textContent, /macOS · 普通独立小窗/);
  assert.match(app.get('connection-detail').textContent, /不代表店铺已登录/);
  assert.deepEqual(app.calls.filter(x => x[0] === 'request'), [['request', 'get_capabilities']]);
});

test('a failed handshake is visible and Retry can restore connection', async () => {
  const app = await page({ failure: true });
  assert.equal(app.get('connection-title').textContent, '等待连接本地助手');
  assert.equal(app.get('connection-detail').textContent, 'Fixture connection failure');
  assert.equal(app.get('connection-dot').className, 'state-dot error');
  assert.equal(app.get('check').disabled, false);
  await app.reconnect();
  assert.equal(app.get('connection-title').textContent, '本地助手已连接');
  assert.equal(app.get('connection-dot').className, 'state-dot connected');
});

test('Windows capability controls whether onboarding claims pin support', async () => {
  const app = await page({ os: 'win', pinCapability: false });
  assert.match(app.get('connection-detail').textContent, /Windows · 普通独立小窗/);
  assert.doesNotMatch(app.get('connection-detail').textContent, /支持置顶/);
});

test('the actual runtime extension ID is copied rather than the development ID', async () => {
  const app = await page();
  assert.equal(app.get('extension-id').textContent, app.id);
  assert.equal(app.get('copy-id').disabled, false);
  await app.get('copy-id').fire('click');
  assert.deepEqual(app.copied, [app.id]);
  assert.equal(app.get('copy-status').textContent, '已复制扩展 ID。');
});

test('clipboard failure gives manual-copy guidance without claiming success', async () => {
  const app = await page({ clipboardFailure: true });
  await app.get('copy-id').fire('click');
  assert.deepEqual(app.copied, []);
  assert.equal(app.get('copy-status').textContent, '请选中上方 ID 后复制。');
});

test('missing metadata or browser platform APIs do not fabricate a download or extension identity', async () => {
  const app = await page({ metadataFailure: true, noRuntime: true, failure: true });
  assert.equal(app.get('download-pending').hidden, false);
  assert.equal(app.get('download').href, '');
  assert.equal(app.get('copy-id').disabled, true);
  assert.equal(app.get('extension-id').textContent, '');
  assert.match(app.get('platform-instruction').textContent, /请选择与你电脑匹配的版本/);
});

(async () => {
  let passed = 0;
  for (const item of tests) {
    try { await item.body(); passed++; console.log('PASS ', item.name); }
    catch (error) { console.error('FAIL ', item.name, error); }
  }
  console.log(`\n${passed}/${tests.length} onboarding checks passed with in-memory fixtures only.`);
  if (passed !== tests.length) process.exitCode = 1;
})();
