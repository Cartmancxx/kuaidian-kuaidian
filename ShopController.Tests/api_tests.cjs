// Executes the production API adapter with in-memory Chrome messaging only.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.resolve(__dirname, '../ShopController/extension/api.js'), 'utf8');
const capability = { hostVersion: '1.0.0', protocolVersion: 1, platform: 'windows', capabilities: { pin: true } };

function fixture(options = {}) {
  const messages = [];
  let firstFailure = !!options.firstFailure;
  const chrome = options.noRuntime ? {} : { runtime: {
    id: 'abcdefghijklmnopabcdefghijklmnop',
    async sendMessage(message) {
      messages.push(structuredClone(message));
      if (firstFailure) { firstFailure = false; return { ok: false, connectionError: true, error: 'Not connected' }; }
      if (message.action === 'get_capabilities') return { ok: true, data: options.capability ?? capability };
      return { ok: true, data: { action: message.action, fixture: true } };
    }
  } };
  const context = vm.createContext({ chrome, location: { search: '?demo=1' }, URLSearchParams });
  const api = vm.runInContext(source.replace(/\bexport\s+/g, '') + '\n;({isDemo,request,getCapabilities});', context);
  return { api, messages };
}
const tests = [];
const test = (name, body) => tests.push({ name, body });

test('production code ignores demo query and contains no demo import', async () => {
  const app = fixture();
  assert.equal(app.api.isDemo, false);
  assert.doesNotMatch(source, /import\s*\([^)]*demo|from\s*['"][^'"]*demo/);
  await app.api.request('get_state');
  assert.deepEqual(app.messages.map(x => x.action), ['get_capabilities', 'get_state']);
});

test('concurrent ordinary requests share one capability handshake', async () => {
  const app = fixture();
  await Promise.all([app.api.request('get_state'), app.api.request('plan_assignments')]);
  assert.equal(app.messages.filter(x => x.action === 'get_capabilities').length, 1);
  assert.equal(app.messages.length, 3);
});

for (const [name, invalid] of [
  ['wrong protocol', { ...capability, protocolVersion: 2 }],
  ['missing version', { protocolVersion: 1, platform: 'windows', capabilities: { pin: true } }],
  ['non-boolean pin capability', { ...capability, capabilities: { pin: 'true' } }],
  ['unsupported platform', { ...capability, platform: 'linux' }],
]) {
  test(`${name} blocks mutations before they are sent`, async () => {
    const app = fixture({ capability: invalid });
    await assert.rejects(app.api.request('save_shop', { shop: { name: 'fixture' } }));
    assert.deepEqual(app.messages.map(x => x.action), ['get_capabilities']);
  });
}

test('Mac capability is accepted without fabricating Windows pin support', async () => {
  const app = fixture({ capability: { ...capability, platform: 'macos', capabilities: { pin: false } } });
  const data = await app.api.getCapabilities();
  assert.equal(data.platform, 'macos');
  assert.equal(data.capabilities.pin, false);
  await app.api.request('get_state');
  assert.equal(app.messages.length, 2);
});

test('failed handshake is cleared and can reconnect without fake state', async () => {
  const app = fixture({ firstFailure: true });
  await assert.rejects(app.api.request('open_shop'), error => error.connectionError === true);
  await app.api.request('get_state');
  assert.deepEqual(app.messages.map(x => x.action), ['get_capabilities', 'get_capabilities', 'get_state']);
});

test('explicit capabilities refresh rechecks the host', async () => {
  const app = fixture();
  await app.api.getCapabilities();
  await app.api.request('get_capabilities');
  assert.deepEqual(app.messages.map(x => x.action), ['get_capabilities', 'get_capabilities']);
});

test('ordinary web pages do not receive a mock native connection', async () => {
  const app = fixture({ noRuntime: true });
  await assert.rejects(app.api.request('get_state'));
  assert.equal(app.messages.length, 0);
});

(async () => {
  let passed = 0;
  for (const item of tests) {
    try { await item.body(); passed++; console.log('PASS ', item.name); }
    catch (error) { console.error('FAIL ', item.name, error); }
  }
  console.log(`\n${passed}/${tests.length} production API checks passed. No browser or native host accessed.`);
  if (passed !== tests.length) process.exitCode = 1;
})();
