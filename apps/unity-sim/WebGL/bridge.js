(() => {
  const build = __HOMATE_BUILD_STATUS__;
  const viewIds = new Set(build.views.map(view => view.id));
  const deviceIds = new Set((build.focusDevices ?? []).map(device => device.id));
  const notify = data => window.parent.postMessage(data, window.location.origin);
  const audio = window.homateCreateSpeakerAudio?.(build, notify);
  window.homateSetAudioEnabled = enabled => audio?.setEnabled(enabled);
  const ready = () => notify({ type: 'homate:ready' });
  window.addEventListener('homate-device-selected', event => {
    if (event.detail === '' || deviceIds.has(event.detail)) notify({ type: 'homate:device-selected', deviceId: event.detail });
  });
  window.addEventListener('homate-unity-ready', ready);
  window.addEventListener('contextmenu', event => event.preventDefault());
  let wheelRemainder = 0;
  window.addEventListener('wheel', event => {
    if (!window.homateUnityInstance) return;
    window.focus?.();
    event.preventDefault();
    const delta = event.deltaY * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? 100 : 1);
    if (!Number.isFinite(delta)) return;
    if (Math.sign(delta) !== Math.sign(wheelRemainder)) wheelRemainder = 0;
    wheelRemainder += delta;
    const steps = Math.min(3, Math.floor(Math.abs(wheelRemainder) / 100));
    for (let i = 0; i < steps; i++) window.homateUnityInstance.SendMessage('HomeMatePreviewCamera', 'Zoom', wheelRemainder < 0 ? 'in' : 'out');
    wheelRemainder -= Math.sign(wheelRemainder) * steps * 100;
  }, { passive: false });
  window.addEventListener('message', event => {
    if (event.origin !== window.location.origin || event.source !== window.parent) return;
    if (!window.homateUnityInstance) return;
    if (event.data?.type === 'homate:request-ready') { ready(); return; }
    if (event.data?.type === 'homate:zoom' && ['in', 'out'].includes(event.data.direction)) {
      window.homateUnityInstance.SendMessage('HomeMatePreviewCamera', 'Zoom', event.data.direction);
      return;
    }
    if (event.data?.type === 'homate:select-device' && (event.data.deviceId === '' || deviceIds.has(event.data.deviceId))) {
      window.homateUnityInstance.SendMessage('HomeMateDevices', 'SelectDevice', event.data.deviceId);
      return;
    }
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
