const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const vm = require('node:vm');

function bridge() {
  const listeners = {};
  const sent = [];
  const parent = { postMessage() {} };
  const window = {
    parent, location: { origin: 'http://localhost' },
    addEventListener(type, callback) { listeners[type] = callback; },
    homateUnityInstance: { SendMessage(...args) { sent.push(args); } },
  };
  const source = readFileSync(resolve(__dirname, '../../unity-sim/WebGL/bridge.js'), 'utf8')
    .replace('__HOMATE_BUILD_STATUS__', JSON.stringify({ views: [{ id: 'living' }], focusDevices: [{ id: 'cam-living' }] }));
  vm.runInNewContext(source, { window });
  return { sent, deliver(data, overrides = {}) {
    listeners.message({ origin: window.location.origin, source: parent, data, ...overrides });
  } };
}

test('device snapshots reject untrusted windows and malformed state', () => {
  const b = bridge();
  const message = { type: 'homate:device-snapshot', devices: [{ id: 'light-living', power: true, brightness: 50, position: 0 }] };
  b.deliver(message, { origin: 'https://untrusted.invalid' });
  b.deliver(message, { source: {} });
  b.deliver({ type: message.type, devices: 'invalid' });
  assert.equal(b.sent.length, 0);
  b.deliver({ type: message.type, devices: [{ ...message.devices[0], brightness: NaN }] });
  assert.deepEqual(JSON.parse(b.sent[0][2]), { devices: [] });
});

test('bridge forwards only supported state fields to the Unity receiver', () => {
  const b = bridge();
  b.deliver({ type: 'homate:device-snapshot', devices: [{ id: 'curtain', power: false, brightness: 100, position: 70, arbitrary: 'discard' }] });
  assert.deepEqual(b.sent[0].slice(0, 2), ['HomeMateDevices', 'ApplySnapshot']);
  assert.deepEqual(JSON.parse(b.sent[0][2]), { devices: [{ id: 'curtain', power: false, brightness: 100, position: 70, recording: false, volume: 0, speed: 0 }] });
  b.deliver({ type: 'homate:set-view', viewId: 'not-in-build' });
  assert.equal(b.sent.length, 1);
});

test('camera, speaker and extractor state is validated and forwarded; focus uses build whitelist', () => {
  const b = bridge();
  b.deliver({ type: 'homate:device-snapshot', devices: [
    { id: 'cam-living', power: false, brightness: 100, position: 0, recording: true, volume: 150, speed: 8 },
    { id: 'bad', power: false, brightness: 100, position: 0, recording: 'yes' },
    { id: 'bad-volume', power: true, brightness: 100, position: 0, volume: NaN },
  ] });
  assert.deepEqual(JSON.parse(b.sent[0][2]).devices, [{ id: 'cam-living', power: false, brightness: 100, position: 0, recording: true, volume: 100, speed: 3 }]);
  b.deliver({ type: 'homate:focus-device', deviceId: 'unknown' });
  assert.equal(b.sent.length, 1);
  b.deliver({ type: 'homate:focus-device', deviceId: 'cam-living' });
  assert.deepEqual(b.sent[1], ['HomeMateDevices', 'FocusDevice', 'cam-living']);
});
