(() => {
  const build = __HOMATE_BUILD_STATUS__;
  const viewIds = new Set(build.views.map(view => view.id));
  const deviceIds = new Set((build.focusDevices ?? []).map(device => device.id));
  const notify = data => window.parent.postMessage(data, window.location.origin);
  const audio = window.homateCreateSpeakerAudio?.(build, notify);
  window.homateSetAudioEnabled = enabled => audio?.setEnabled(enabled);
  const ready = () => notify({ type: 'homate:ready' });
  window.addEventListener('homate-unity-ready', ready);
  window.addEventListener('message', event => {
    if (event.origin !== window.location.origin || event.source !== window.parent) return;
    if (!window.homateUnityInstance) return;
    if (event.data?.type === 'homate:request-ready') { ready(); return; }
    if (event.data?.type === 'homate:focus-device' && deviceIds.has(event.data.deviceId)) {
      window.homateUnityInstance.SendMessage('HomeMateDevices', 'FocusDevice', event.data.deviceId);
      notify({ type: 'homate:device-focused', deviceId: event.data.deviceId });
      return;
    }
    if (event.data?.type === 'homate:device-snapshot') {
      if (!Array.isArray(event.data.devices) || event.data.devices.length > 256) return;
      const devices = event.data.devices.filter(device =>
        typeof device?.id === 'string' && device.id.length <= 100 &&
        typeof device.power === 'boolean' && Number.isFinite(device.brightness) && Number.isFinite(device.position) &&
        (device.recording === undefined || typeof device.recording === 'boolean') &&
        (device.volume === undefined || Number.isFinite(device.volume)) && (device.speed === undefined || Number.isFinite(device.speed))
      ).map(({ id, power, brightness, position, recording = false, volume = 0, speed = 0 }) =>
        ({ id, power, brightness, position, recording, volume: Math.max(0, Math.min(100, volume)), speed: Math.max(0, Math.min(3, speed)) }));
      window.homateUnityInstance.SendMessage('HomeMateDevices', 'ApplySnapshot', JSON.stringify({ devices }));
      audio?.update(devices);
      return;
    }
    if (event.data?.type !== 'homate:set-view' || !viewIds.has(event.data.viewId)) return;
    window.homateUnityInstance.SendMessage('HomeMatePreviewCamera', 'SelectView', event.data.viewId);
    notify({ type: 'homate:view-changed', viewId: event.data.viewId });
  });
  if (window.homateUnityInstance) ready();
})();
