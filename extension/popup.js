const SERVER_URL = 'http://doubleaaguy.duckdns.org:8081';

const $ = id => document.getElementById(id);

const detectedBox     = $('detectedBox');
const detectedServer  = $('detectedServer');
const groupsSlider    = $('groupsSlider');
const groupsVal       = $('groupsVal');
const targetX         = $('targetX');
const targetY         = $('targetY');
const statusText      = $('statusText');
const botsText        = $('botsText');
const targetXDisplay  = $('targetXDisplay');
const targetYDisplay  = $('targetYDisplay');
const groupsDisplay   = $('groupsDisplay');
const errorText       = $('errorText');
const manualToggle    = $('manualToggle');
const manualFields    = $('manualFields');
const serverIp        = $('serverIp');
const serverPort      = $('serverPort');
const serverPath      = $('serverPath');

let pollTimer = null;
let autoServer = null; // { ip, port, path } detected from slither.io

// --- helpers ----------------------------------------------------------------

function showError(msg) {
  errorText.textContent = msg;
  if (msg) console.warn('BotControl:', msg);
}

async function apiGet(path) {
  const r = await fetch(`${SERVER_URL}${path}`);
  if (!r.ok) {
    const body = await r.text().catch(() => '');
    throw new Error(`${r.status} ${r.statusText}${body ? ': ' + body : ''}`);
  }
  return r.json();
}

function getServerInfo() {
  if (autoServer) return autoServer;
  return {
    ip: serverIp.value.trim() || '192.211.52.146',
    port: serverPort.value.trim() || '444',
    path: serverPath.value.trim() || '/slither',
  };
}

async function apiStart() {
  const s = getServerInfo();
  const grps = parseInt(groupsSlider.value) || 4;
  const path = encodeURIComponent(s.path);
  return apiGet(`/start/${s.ip}:${s.port}/${grps}?path=${path}`);
}

async function apiStop() {
  return apiGet('/stop');
}

async function apiEdit(x, y) {
  return apiGet(`/edit?x=${x}&y=${y}`);
}

async function apiStatus() {
  return apiGet('/status');
}

// --- auto-detect server from slither.io ------------------------------------

async function detectServerFromTab() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  const tab = tabs[0];
  if (!tab || !tab.url) return;

  const isSlither = /slither\.(io|com)/.test(tab.url);
  if (!isSlither) return;

  try {
    const resp = await chrome.tabs.sendMessage(tab.id, { type: 'get_server' });
    if (resp && resp.ip) {
      autoServer = resp;
      detectedServer.textContent = `${resp.ip}:${resp.port}`;
      detectedBox.style.display = 'flex';
    }
  } catch (_) {
    // content script not ready yet
  }
}

// Listen for push notifications from content script
chrome.runtime.onMessage.addListener((msg) => {
  if (msg && msg.type === 'server_detected' && msg.data) {
    autoServer = msg.data;
    detectedServer.textContent = `${msg.data.ip}:${msg.data.port}`;
    detectedBox.style.display = 'flex';
  }
});

// --- update UI --------------------------------------------------------------

function updateStatus(data) {
  const running = data.running !== undefined ? data.running : '?';
  const target  = data.target || {};
  const groups  = data.groups !== undefined ? data.groups : '?';
  const total   = data.total_bots !== undefined ? data.total_bots : '?';

  statusText.textContent = running > 0 ? '● running' : '○ stopped';
  statusText.className   = 'val' + (running > 0 ? ' green' : '');
  botsText.textContent   = `${running} / ${total}`;
  targetXDisplay.textContent = target.x ?? '?';
  targetYDisplay.textContent = target.y ?? '?';
  groupsDisplay.textContent  = groups;
}

async function pollStatus() {
  try {
    const data = await apiStatus();
    updateStatus(data);
    showError('');
  } catch (e) {
    statusText.textContent = '⚠ offline';
    statusText.className   = 'val red';
    showError(String(e));
  }
}

// --- buttons ----------------------------------------------------------------

$('btnStart').addEventListener('click', async () => {
  showError('');
  $('btnStart').disabled = true;
  try {
    const data = await apiStart();
    updateStatus(data);
    showError('');
  } catch (e) {
    showError('Start failed: ' + e.message);
  } finally {
    $('btnStart').disabled = false;
  }
});

$('btnStop').addEventListener('click', async () => {
  showError('');
  $('btnStop').disabled = true;
  try {
    await apiStop();
    updateStatus({ running: 0, target: {}, groups: 0, total_bots: 0 });
    showError('');
  } catch (e) {
    showError('Stop failed: ' + e.message);
  } finally {
    $('btnStop').disabled = false;
  }
});

$('btnEdit').addEventListener('click', async () => {
  showError('');
  const x = parseInt(targetX.value) || 30000;
  const y = parseInt(targetY.value) || 30000;
  $('btnEdit').disabled = true;
  try {
    await apiEdit(x, y);
    targetXDisplay.textContent = x;
    targetYDisplay.textContent = y;
    showError('');
  } catch (e) {
    showError('Edit failed: ' + e.message);
  } finally {
    $('btnEdit').disabled = false;
  }
});

// --- slider -----------------------------------------------------------------

groupsSlider.addEventListener('input', () => {
  groupsVal.textContent = groupsSlider.value;
});

// --- manual toggle ----------------------------------------------------------

manualToggle.addEventListener('click', () => {
  const show = manualFields.classList.toggle('visible');
  manualToggle.textContent = show ? '− Hide manual config' : '＋ Manual server config';
});

// --- auto-poll --------------------------------------------------------------

function startPolling() {
  stopPolling();
  pollStatus();
  pollTimer = setInterval(pollStatus, 3000);
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
}

// --- persist settings -------------------------------------------------------

function saveSettings() {
  const s = {
    groups: groupsSlider.value,
    targetX: targetX.value,
    targetY: targetY.value,
    serverIp: serverIp.value,
    serverPort: serverPort.value,
    serverPath: serverPath.value,
  };
  chrome.storage.local.set({ botControl: s });
}

function loadSettings() {
  chrome.storage.local.get('botControl', (result) => {
    const s = result.botControl || {};
    if (s.groups)     { groupsSlider.value = s.groups; groupsVal.textContent = s.groups; }
    if (s.targetX)    targetX.value = s.targetX;
    if (s.targetY)    targetY.value = s.targetY;
    if (s.serverIp)   serverIp.value = s.serverIp;
    if (s.serverPort) serverPort.value = s.serverPort;
    if (s.serverPath) serverPath.value = s.serverPath;
  });
}

[groupsSlider, targetX, targetY, serverIp, serverPort, serverPath].forEach(el => {
  el.addEventListener('change', saveSettings);
  el.addEventListener('input', () => {
    if (el !== groupsSlider) saveSettings();
  });
});

// --- init -------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
  loadSettings();
  detectServerFromTab();
  startPolling();
});

window.addEventListener('unload', stopPolling);
