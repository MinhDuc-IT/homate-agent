mergeInto(LibraryManager.library, {
  HomateDeviceSelected: function (id) {
    window.dispatchEvent(new CustomEvent('homate-device-selected', { detail: UTF8ToString(id) }));
  }
});
