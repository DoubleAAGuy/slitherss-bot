// Intercept WebSocket connections to auto-detect the slither.io game server
(function () {
  const OriginalWebSocket = window.WebSocket;
  let detectedServer = null;

  window.WebSocket = function (url, protocols) {
    try {
      const urlStr = typeof url === 'string' ? url : url.toString();
      if (urlStr.startsWith('ws://') || urlStr.startsWith('wss://')) {
        const u = new URL(urlStr);
        if (u.pathname === '/slither' || u.pathname.startsWith('/slither')) {
          detectedServer = {
            ip: u.hostname,
            port: u.port || '444',
            path: u.pathname,
          };
          chrome.runtime.sendMessage({ type: 'server_detected', data: detectedServer });
        }
      }
    } catch (_) {}

    return protocols !== undefined
      ? new OriginalWebSocket(url, protocols)
      : new OriginalWebSocket(url);
  };

  window.WebSocket.prototype = OriginalWebSocket.prototype;
  window.WebSocket.CONNECTING = OriginalWebSocket.CONNECTING;
  window.WebSocket.OPEN = OriginalWebSocket.OPEN;
  window.WebSocket.CLOSING = OriginalWebSocket.CLOSING;
  window.WebSocket.CLOSED = OriginalWebSocket.CLOSED;

  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg && msg.type === 'get_server') {
      sendResponse(detectedServer);
    }
  });
})();
