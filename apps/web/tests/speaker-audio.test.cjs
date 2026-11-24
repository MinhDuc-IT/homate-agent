const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const vm = require('node:vm');

function player() {
  let audio;
  class FakeAudio {
    constructor() { audio = this; this.paused = true; this.listeners = {}; this.playCalls = 0; }
    addEventListener(type, callback) { this.listeners[type] = callback; }
    getAttribute(key) { return this[key] ?? null; }
    removeAttribute(key) { delete this[key]; }
    pause() { this.paused = true; }
    play() {
      this.playCalls++;
      if (this.reject) return Promise.reject(new Error('autoplay blocked'));
      this.paused = false;
      return Promise.resolve();
    }
  }
  const window = { addEventListener() {} };
  vm.runInNewContext(readFileSync(resolve(__dirname, '../../unity-sim/WebGL/speaker-audio.js'), 'utf8'), { window, Audio: FakeAudio });
  const messages = [];
  const controller = window.homateCreateSpeakerAudio({ speakerId: 'speaker-living', speakerAudio: ['audio/track-1.mp3', 'audio/track-2.mp3', 'https://invalid.example/music.mp3'] }, message => messages.push(message));
  return { controller, audio, messages };
}
const state = (power, volume) => [{ id: 'speaker-living', power, volume }];

test('speaker audio requires opt-in and follows power, mute and volume without restarting every snapshot', async () => {
  const { controller, audio } = player();
  controller.update(state(true, 35));
  assert.equal(audio.playCalls, 0);
  assert.equal(audio.src, undefined);
  controller.setEnabled(true);
  await Promise.resolve();
  assert.equal(audio.playCalls, 1);
  assert.equal(audio.src, 'audio/track-1.mp3');
  assert.equal(audio.volume, 0.35);
  controller.update(state(true, 80));
  assert.equal(audio.volume, 0.8);
  assert.equal(audio.playCalls, 1);
  controller.update(state(false, 80));
  assert.equal(audio.paused, true);
  controller.update(state(true, 0));
  assert.equal(audio.paused, true);
  controller.update(state(true, 40));
  assert.equal(audio.paused, false);
  controller.setEnabled(false);
  assert.equal(audio.paused, true);
});

test('playlist advances and loops only through generated local tracks', () => {
  const { controller, audio } = player();
  controller.update(state(true, 35));
  controller.setEnabled(true);
  audio.paused = true;
  audio.listeners.ended();
  assert.equal(audio.src, 'audio/track-2.mp3');
  assert.equal(audio.paused, false);
  audio.paused = true;
  audio.listeners.ended();
  assert.equal(audio.src, 'audio/track-1.mp3');
});

test('blocked playback and loading failures return to opt-in without unhandled rejection', async () => {
  const { controller, audio, messages } = player();
  controller.update(state(true, 35));
  audio.reject = true;
  controller.setEnabled(true);
  await new Promise(setImmediate);
  assert.equal(messages.at(-1).blocked, true);
  assert.equal(messages.at(-1).enabled, false);
  assert.equal(audio.paused, true);
  audio.reject = false;
  controller.setEnabled(true);
  audio.listeners.error();
  assert.equal(audio.src, undefined);
  assert.equal(messages.at(-1).failed, true);
  controller.setEnabled(true);
  assert.equal(audio.src, 'audio/track-1.mp3');
});
