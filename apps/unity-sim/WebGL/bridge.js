(() => {
  const build = __HOMATE_BUILD_STATUS__;
  const viewIds = new Set(build.views.map(view => view.id));
  const notify = data => window.parent.postMessage(data, window.location.origin);
  const ready = () => notify({ type: 'homate:ready' });
  window.addEventListener('homate-unity-ready', ready);
  window.addEventListener('message', event => {
    if (event.origin !== window.location.origin || event.source !== window.parent) return;
    if (event.data?.type !== 'homate:set-view' || !viewIds.has(event.data.viewId)) return;
    if (!window.homateUnityInstance) return;
    window.homateUnityInstance.SendMessage('HomeMatePreviewCamera', 'SelectView', event.data.viewId);
    notify({ type: 'homate:view-changed', viewId: event.data.viewId });
  });
  if (window.homateUnityInstance) ready();
})();
