// Stream the original speaker playlist separately from the Unity heap.
// Sound is opt-in and starts only from an explicit browser user gesture.
window.homateCreateSpeakerAudio = (build, notify) => {
  const tracks = Array.isArray(build.speakerAudio)
    ? build.speakerAudio.filter(path => /^audio\/track-[1-9][0-9]*\.mp3$/.test(path)) : [];
  if (!tracks.length || typeof build.speakerId !== 'string') return null;
  const audio = new Audio();
  audio.preload = 'none';
  let enabled = false;
  let speaker = null;
  let track = 0;
  const status = () => notify({ type: 'homate:audio-state', enabled, playing: !audio.paused });
  const sync = () => {
    audio.volume = Math.max(0, Math.min(100, speaker?.volume ?? 0)) / 100;
    if (!enabled || !speaker?.power || audio.volume === 0) {
      audio.pause();
      status();
      return;
    }
    if (!audio.getAttribute('src')) audio.src = tracks[track];
    if (!audio.paused) { status(); return; }
    // play() runs synchronously inside the click when sound is enabled.
    const pending = audio.play();
    pending?.then(status).catch(() => {
      enabled = false;
      audio.pause();
      notify({ type: 'homate:audio-state', enabled: false, playing: false, blocked: true });
    });
  };
  audio.addEventListener('ended', () => {
    track = (track + 1) % tracks.length;
    audio.src = tracks[track];
    sync();
  });
  audio.addEventListener('error', () => {
    enabled = false;
    audio.pause();
    audio.removeAttribute('src');
    notify({ type: 'homate:audio-state', enabled: false, playing: false, failed: true });
  });
  window.addEventListener('pagehide', () => audio.pause());
  return {
    update(devices) {
      speaker = devices.find(device => device.id === build.speakerId) ?? null;
      sync();
    },
    setEnabled(value) {
      enabled = value === true;
      sync();
      status();
    },
  };
};
