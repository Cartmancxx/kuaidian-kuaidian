// Deterministic worker tests. All Chrome APIs below are in-memory mocks.
// No browser, real profile, registry, native host, or network is accessed.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const extension = path.resolve(__dirname, '../ShopController/extension');
const source = fs.readFileSync(path.join(extension, 'background.js'), 'utf8');
const manifest = JSON.parse(fs.readFileSync(path.join(extension, 'manifest.json'), 'utf8'));
const extensionId = 'hadeebhijljjdebkaiaglaeipajnnind';
const origin = `chrome-extension://${extensionId}/`;
const clone = value => JSON.parse(JSON.stringify(value));

function fixture() {
  return {
    storage: {}, windows: new Map(), nextId: 10,
    created: [], updated: [], native: [], badges: [], titles: [], errors: [],
    createFailure: false, nativeFailure: false,
  };
}

function worker(state) {
  const listeners = {};
  const chrome = {
    storage: {
      session: {
        async get(key) { return { [key]: state.storage[key] }; },
        async set(value) { Object.assign(state.storage, clone(value)); },
        async remove(key) { delete state.storage[key]; },
      },
    },
    windows: {
      async get(id) {
        if (!state.windows.has(id)) throw new Error('No such window');
        return clone(state.windows.get(id));
      },
      async update(id, update) {
        const current = state.windows.get(id);
        if (!current) throw new Error('No such window');
        state.updated.push({ id, ...clone(update) });
        Object.assign(current, clone(update));
        return clone(current);
      },
      async create(options) {
        if (state.createFailure) throw new Error('Synthetic create failure');
        const created = { id: state.nextId++, state: 'normal', ...clone(options) };
        state.created.push(clone(created));
        state.windows.set(created.id, created);
        return clone(created);
      },
      onRemoved: { addListener(fn) { listeners.removed = fn; } },
    },
    action: {
      onClicked: { addListener(fn) { listeners.click = fn; } },
      async setBadgeText(value) { state.badges.push(clone(value)); },
      async setTitle(value) { state.titles.push(clone(value)); },
    },
    runtime: {
      id: extensionId,
      getURL: value => origin + value,
      onMessage: { addListener(fn) { listeners.message = fn; } },
      sendNativeMessage(host, message, callback) {
        state.native.push({ host, message: clone(message) });
        if (state.nativeFailure) chrome.runtime.lastError = { message: 'Synthetic native failure' };
        callback(state.nativeFailure ? undefined : { ok: true, data: { fixture: true } });
        delete chrome.runtime.lastError;
      },
    },
  };
  const context = vm.createContext({
    chrome,
    console: { error: (...args) => state.errors.push(args.map(String)) },
  });
  vm.runInContext(source, context, { filename: 'background.js' });
  assert.equal(typeof listeners.click, 'function');
  assert.equal(typeof listeners.message, 'function');
  return {
    click() { listeners.click(); },
    request(message, sender = { id: extensionId, url: origin + 'popup.html' }) {
      let response;
      const keptOpen = listeners.message(message, sender, value => { response = clone(value); });
      return { response, keptOpen };
    },
  };
}

// Let async Chrome mock calls and worker continuations finish without a real timer.
async function settle() {
  for (let i = 0; i < 6; i++) await new Promise(resolve => setImmediate(resolve));
}

const tests = [];
function test(name, body) { tests.push({ name, body }); }

test('manifest uses a resident-window action and only nativeMessaging/storage permissions', () => {
  assert.equal(manifest.version, '1.0.0');
  assert.equal(manifest.action.default_popup, undefined);
  assert.deepEqual([...manifest.permissions].sort(), ['nativeMessaging', 'storage'].sort());
  assert.equal(manifest.host_permissions, undefined);
  assert.equal(manifest.content_scripts, undefined);
});

test('first toolbar click creates one compact 320 by 390 popup window', async () => {
  const state = fixture(), app = worker(state);
  app.click(); await settle();
  assert.equal(state.created.length, 1);
  assert.deepEqual(state.created[0], {
    id: 10, state: 'normal', url: origin + 'popup.html?window=1', type: 'popup',
    width: 320, height: 390, focused: true,
  });
  assert.equal(state.storage.launcherWindowId, 10);
  assert.equal(state.native.length, 0);
});

test('rapid concurrent toolbar clicks still create only one window', async () => {
  const state = fixture(), app = worker(state);
  for (let i = 0; i < 20; i++) app.click();
  await settle();
  assert.equal(state.created.length, 1);
});

test('another toolbar click focuses the existing window without duplicating it', async () => {
  const state = fixture(), app = worker(state);
  app.click(); await settle(); app.click(); await settle();
  assert.equal(state.created.length, 1);
  assert.deepEqual(state.updated.at(-1), { id: 10, focused: true });
});

test('service worker restart reuses the window ID from session storage', async () => {
  const state = fixture(), firstWorker = worker(state);
  firstWorker.click(); await settle();
  const restartedWorker = worker(state);
  restartedWorker.click(); await settle();
  assert.equal(state.created.length, 1);
  assert.deepEqual(state.updated.at(-1), { id: 10, focused: true });
});

test('a minimized launcher is restored to normal and focused', async () => {
  const state = fixture(), app = worker(state);
  app.click(); await settle();
  state.windows.get(10).state = 'minimized';
  app.click(); await settle();
  assert.deepEqual(state.updated.at(-1), { id: 10, focused: true, state: 'normal' });
  assert.equal(state.created.length, 1);
});

test('a stale closed-window ID is replaced by a new launcher', async () => {
  const state = fixture(), app = worker(state);
  app.click(); await settle(); state.windows.delete(10);
  app.click(); await settle();
  assert.equal(state.created.length, 2);
  assert.equal(state.storage.launcherWindowId, 11);
});

test('a saved non-popup window is not resized or repurposed', async () => {
  const state = fixture();
  state.storage.launcherWindowId = 7;
  state.windows.set(7, { id: 7, state: 'normal', type: 'normal' });
  worker(state).click(); await settle();
  assert.equal(state.created.length, 1);
  assert.equal(state.updated.length, 0);
  assert.equal(state.windows.get(7).type, 'normal');
});

test('failed creation can be retried without a stuck in-flight lock', async () => {
  const state = fixture(), app = worker(state);
  state.createFailure = true;
  app.click(); await settle();
  assert.equal(state.created.length, 0);
  state.createFailure = false;
  app.click(); await settle();
  assert.equal(state.created.length, 1);
});

test('successful retry clears the failure badge and restores the launcher title', async () => {
  const state = fixture(), app = worker(state);
  state.createFailure = true;
  app.click(); await settle();
  assert.deepEqual(state.badges.at(-1), { text: '!' });
  assert.deepEqual(state.titles.at(-1), { title: '小窗打开失败，请重新点击' });
  state.createFailure = false;
  app.click(); await settle();
  assert.deepEqual(state.badges.at(-1), { text: '' });
  assert.deepEqual(state.titles.at(-1), { title: manifest.action.default_title });
});

test('foreign senders, fake page paths and unknown actions never reach native messaging', () => {
  const state = fixture(), app = worker(state);
  const attempts = [
    [{ action: 'get_state' }, { id: 'another-extension', url: origin + 'popup.html' }],
    [{ action: 'get_state' }, { id: extensionId, url: 'https://example.invalid/popup.html' }],
    [{ action: 'get_state' }, { id: extensionId, url: origin + 'popup.html.evil' }],
    [{ action: 'get_state' }, { id: extensionId, url: origin + 'help.html' }],
    [{ action: 'erase_profile' }, { id: extensionId, url: origin + 'manage.html' }],
    ...['--install-user', '--uninstall-user', 'install_user', 'uninstall_user'].map(action =>
      [{ action }, { id: extensionId, url: origin + 'setup.html' }]),
    [null, { id: extensionId, url: origin + 'manage.html' }],
  ];
  for (const [message, sender] of attempts) {
    const result = app.request(message, sender);
    assert.equal(result.response.ok, false);
    assert.equal(result.keptOpen, false);
  }
  assert.equal(state.native.length, 0);
});

test('only approved extension pages forward supported actions to the fixed native host', () => {
  const state = fixture(), app = worker(state);
  for (const page of ['popup.html?window=1', 'manage.html?view=shops#top']) {
    const result = app.request({ action: 'get_state' }, { id: extensionId, url: origin + page });
    assert.equal(result.keptOpen, true);
    assert.deepEqual(result.response, { ok: true, data: { fixture: true } });
  }
  assert.equal(state.native.length, 2);
  for (const call of state.native) assert.equal(call.host, 'com.shopcontroller.chrome');
});

test('native connection failures are reported rather than replaced with mock shop data', () => {
  const state = fixture(), app = worker(state);
  state.nativeFailure = true;
  const result = app.request({ action: 'get_state' });
  assert.equal(result.response.ok, false);
  assert.equal(result.response.connectionError, true);
  assert.equal(result.response.data, undefined);
});

test('the onboarding page can query capabilities but no page can route native pin commands through the worker', () => {
  const state = fixture(), app = worker(state);
  const result = app.request({ action: 'get_capabilities' }, { id: extensionId, url: origin + 'setup.html' });
  assert.equal(result.response.ok, true);
  assert.deepEqual(state.native.at(-1), { host: 'com.shopcontroller.chrome', message: { action: 'get_capabilities' } });
  for (const page of ['setup.html', 'popup.html', 'manage.html']) {
    for (const action of ['get_launcher_pin', 'set_launcher_pin']) {
      assert.equal(app.request({ action, enabled: true }, { id: extensionId, url: origin + page }).response.ok, false);
    }
  }
  assert.equal(state.native.length, 1);
});

(async () => {
  let passed = 0;
  for (const { name, body } of tests) {
    try { await body(); passed++; process.stdout.write(`PASS  ${name}\n`); }
    catch (error) { process.stderr.write(`FAIL  ${name}\n${error.stack}\n`); }
  }
  process.stdout.write(`\n${passed}/${tests.length} launcher worker checks passed.\n`);
  process.stdout.write('Only in-memory Chrome mocks were used; no real browser, profile, native host, or registry was accessed.\n');
  if (passed !== tests.length) process.exitCode = 1;
})();
