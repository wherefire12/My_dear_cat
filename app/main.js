'use strict';
const { app, BrowserWindow, Tray, Menu, ipcMain, screen, protocol, shell, nativeImage } = require('electron');
const path = require('path');
const fs = require('fs');
const { Readable } = require('stream');

// ---------------------------------------------------------------- basics
app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required');
if (process.platform === 'win32') app.setAppUserModelId('com.hakan.kedi');

protocol.registerSchemesAsPrivileged([{
  scheme: 'kedi',
  privileges: { standard: true, secure: true, supportFetchAPI: true, stream: true, corsEnabled: true },
}]);

const ROOT = app.isPackaged ? path.dirname(process.execPath) : path.join(__dirname, '..');
const VIDEO_DIR = path.join(ROOT, 'videolar');
const RENDER_DIR = path.join(__dirname, 'renderer');
const ICON = path.join(__dirname, 'ikon', 'ikon.png');
const TRAY_ICON = path.join(__dirname, 'ikon', 'tray.png');

const TABAN_G = 372;          // window width (medium size)
const TABAN_Y = 504;          // window height (medium size)
const BOYUTLAR = { kucuk: 0.75, orta: 1, buyuk: 1.3, cok_buyuk: 1.6 };

const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.webm': 'video/webm', '.mp4': 'video/mp4', '.mov': 'video/quicktime', '.png': 'image/png', '.svg': 'image/svg+xml',
};

// ---------------------------------------------------------------- settings file
let CFG_FILE;
const VARSAYILAN = { boyut: 'orta', ustte: false, ses: true, butonlar: 'her_zaman', otomatik: true, x: null, y: null, ilk: true };
let cfg = { ...VARSAYILAN };
function ayarOku() {
  try { cfg = { ...VARSAYILAN, ...JSON.parse(fs.readFileSync(CFG_FILE, 'utf8')) }; } catch { cfg = { ...VARSAYILAN }; }
  if (!BOYUTLAR[cfg.boyut]) cfg.boyut = 'orta';
}
let yazZamanlayici = null;
function ayarYaz() {
  clearTimeout(yazZamanlayici);
  yazZamanlayici = setTimeout(() => {
    try { fs.mkdirSync(path.dirname(CFG_FILE), { recursive: true }); fs.writeFileSync(CFG_FILE, JSON.stringify(cfg, null, 2)); } catch {}
  }, 300);
}

// ---------------------------------------------------------------- helpers
const olcek = () => BOYUTLAR[cfg.boyut] || 1;
const boyut = () => ({ width: Math.round(TABAN_G * olcek()), height: Math.round(TABAN_Y * olcek()) });

function ekranaSigdir(x, y, w, h) {
  const d = screen.getDisplayNearestPoint({ x: Math.round(x + w / 2), y: Math.round(y + h / 2) });
  const a = d.workArea;
  x = Math.min(Math.max(x, a.x), a.x + a.width - w);
  y = Math.min(Math.max(y, a.y), a.y + a.height - h);
  return { x: Math.round(x), y: Math.round(y) };
}
function varsayilanKonum(w, h) {
  const a = screen.getPrimaryDisplay().workArea;
  return { x: a.x + a.width - w - 24, y: a.y + a.height - h - 4 };
}

function klipleriTara() {
  const out = {};
  let dirs = [];
  try { dirs = fs.readdirSync(VIDEO_DIR, { withFileTypes: true }).filter(d => d.isDirectory()); } catch {}
  for (const d of dirs) {
    let files = [];
    try { files = fs.readdirSync(path.join(VIDEO_DIR, d.name)); } catch {}
    out[d.name] = files
      .filter(f => /\.(webm|mp4|mov)$/i.test(f))
      .sort()
      .map(f => ({
        ad: f,
        url: `kedi://local/videolar/${encodeURIComponent(d.name)}/${encodeURIComponent(f)}`,
        kart: !/\.webm$/i.test(f),   // mp4/mov has no alpha: shown as a framed card
      }));
  }
  return out;
}

// ---------------------------------------------------------------- kedi:// protocol (with Range support for video)
function dosyaYaniti(file, req) {
  let st;
  try { st = fs.statSync(file); } catch { return new Response('bulunamadı', { status: 404 }); }
  if (!st.isFile()) return new Response('bulunamadı', { status: 404 });
  const type = MIME[path.extname(file).toLowerCase()] || 'application/octet-stream';
  const range = req.headers.get('range');
  if (range) {
    const m = /bytes=(\d*)-(\d*)/.exec(range);
    let start = 0, end = st.size - 1;
    if (m) {
      if (m[1] === '' && m[2] !== '') { start = Math.max(0, st.size - Number(m[2])); }
      else { start = Number(m[1] || 0); if (m[2] !== '') end = Math.min(Number(m[2]), st.size - 1); }
    }
    if (start >= st.size) return new Response(null, { status: 416, headers: { 'Content-Range': `bytes */${st.size}` } });
    return new Response(Readable.toWeb(fs.createReadStream(file, { start, end })), {
      status: 206,
      headers: { 'Content-Type': type, 'Content-Length': String(end - start + 1),
        'Content-Range': `bytes ${start}-${end}/${st.size}`, 'Accept-Ranges': 'bytes' },
    });
  }
  return new Response(Readable.toWeb(fs.createReadStream(file)), {
    status: 200, headers: { 'Content-Type': type, 'Content-Length': String(st.size), 'Accept-Ranges': 'bytes' },
  });
}
function protokoluKur() {
  protocol.handle('kedi', (req) => {
    const u = new URL(req.url);
    const p = decodeURIComponent(u.pathname);
    let base, rel;
    if (p.startsWith('/app/')) { base = RENDER_DIR; rel = p.slice(5); }
    else if (p.startsWith('/videolar/')) { base = VIDEO_DIR; rel = p.slice(10); }
    else return new Response('bulunamadı', { status: 404 });
    const file = path.normalize(path.join(base, rel));
    if (!file.startsWith(path.normalize(base + path.sep))) return new Response('yasak', { status: 403 });
    return dosyaYaniti(file, req);
  });
}

// ---------------------------------------------------------------- window
let win = null, tray = null, konfetiWin = null;

function ayarlariGonder() {
  if (win && !win.isDestroyed()) win.webContents.send('ayarlar', { ses: cfg.ses, butonlar: cfg.butonlar });
}

function pencereOlustur() {
  const { width, height } = boyut();
  let pos = (cfg.x != null && cfg.y != null) ? { x: cfg.x, y: cfg.y } : varsayilanKonum(width, height);
  pos = ekranaSigdir(pos.x, pos.y, width, height);

  win = new BrowserWindow({
    ...pos, width, height,
    transparent: true, frame: false, resizable: false, maximizable: false, minimizable: false,
    fullscreenable: false, skipTaskbar: true, hasShadow: false, backgroundColor: '#00000000',
    alwaysOnTop: cfg.ustte, show: false, title: 'Kedi', icon: ICON, thickFrame: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true, nodeIntegration: false, backgroundThrottling: false, spellcheck: false,
    },
  });
  if (cfg.ustte) win.setAlwaysOnTop(true, 'floating');
  win.setIgnoreMouseEvents(true, { forward: true });
  win.webContents.on('did-finish-load', () => { win.webContents.setZoomFactor(olcek()); ayarlariGonder(); });
  win.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  win.webContents.on('will-navigate', (e) => e.preventDefault());
  win.once('ready-to-show', () => win.showInactive());
  win.on('show', menuyuKur);
  win.on('hide', menuyuKur);
  // Window closed (e.g. Alt+F4): forget it and quit the whole app cleanly,
  // so no timer ever touches a destroyed window.
  win.on('closed', () => {
    win = null;
    if (surukle) { clearInterval(surukle.t); surukle = null; }
    app.quit();
  });
  if (process.env.KEDI_TEST) require('./test-scenario.js')(win, app, process.env.KEDI_TEST);
  win.loadURL('kedi://local/app/index.html');
}

function konumuKaydet() {
  if (!win) return;
  const b = win.getBounds();
  cfg.x = b.x; cfg.y = b.y; ayarYaz();
}

function boyutDegistir(yeni) {
  if (!BOYUTLAR[yeni] || !win) return;
  const eski = win.getBounds();
  cfg.boyut = yeni;
  const { width, height } = boyut();
  // keep the bottom-centre fixed so the cat grows/shrinks in place
  let x = eski.x + (eski.width - width) / 2, y = eski.y + eski.height - height;
  ({ x, y } = ekranaSigdir(x, y, width, height));
  win.setBounds({ x, y, width, height });
  win.webContents.setZoomFactor(olcek());
  konumuKaydet(); menuyuKur();
}

function tumEkranlaraSigdir() {
  if (!win) return;
  const b = win.getBounds();
  const p = ekranaSigdir(b.x, b.y, b.width, b.height);
  if (p.x !== b.x || p.y !== b.y) { win.setBounds({ ...p, width: b.width, height: b.height }); konumuKaydet(); }
}

// ---------------------------------------------------------------- dragging
let surukle = null;
ipcMain.on('drag-start', () => {
  if (!win || surukle) return;
  const c = screen.getCursorScreenPoint();
  const b = win.getBounds();
  surukle = { ox: c.x - b.x, oy: c.y - b.y, sx: c.x, sy: c.y, w: b.width, h: b.height, moved: false };
  surukle.t = setInterval(() => {
    if (!surukle || !win) return;
    const p = screen.getCursorScreenPoint();
    if (!surukle.moved && Math.hypot(p.x - surukle.sx, p.y - surukle.sy) > 5) surukle.moved = true;
    if (surukle.moved) win.setBounds({ x: p.x - surukle.ox, y: p.y - surukle.oy, width: surukle.w, height: surukle.h });
  }, 10);
});
ipcMain.handle('drag-end', () => {
  if (!surukle) return { moved: false };
  clearInterval(surukle.t);
  const moved = surukle.moved;
  surukle = null;
  if (moved) { tumEkranlaraSigdir(); konumuKaydet(); }
  return { moved };
});

// ---------------------------------------------------------------- click-through / proximity
ipcMain.on('fare-gecsin', (_e, gecsin) => {
  if (!win || surukle) return;
  if (gecsin) win.setIgnoreMouseEvents(true, { forward: true });
  else win.setIgnoreMouseEvents(false);
});

let yakindi = false;
let yakinlikZ = null;
function yakinlikTakibi() {
  yakinlikZ = setInterval(() => {
    if (!win || win.isDestroyed() || !win.isVisible() || surukle) return;
    const c = screen.getCursorScreenPoint();
    const b = win.getBounds();
    // the stage area where the cat sits (buttons excluded)
    const sx = b.x, sy = b.y, sw = b.width, sh = b.height * 0.87;
    const dx = Math.max(sx - c.x, 0, c.x - (sx + sw));
    const dy = Math.max(sy - c.y, 0, c.y - (sy + sh));
    const d = Math.hypot(dx, dy);
    const yakinEsik = 110 * olcek(), uzakEsik = 260 * olcek();
    if (!yakindi && d < yakinEsik) { yakindi = true; win.webContents.send('yakin'); }
    else if (yakindi && d > uzakEsik) yakindi = false;
  }, 150);
}

// ---------------------------------------------------------------- confetti (full screen)
ipcMain.on('parti', () => {
  if (!win) return;
  const b = win.getBounds();
  const disp = screen.getDisplayMatching(b);
  const db = disp.bounds;
  if (konfetiWin && !konfetiWin.isDestroyed()) konfetiWin.destroy();
  konfetiWin = new BrowserWindow({
    x: db.x, y: db.y, width: db.width, height: db.height,
    transparent: true, frame: false, focusable: false, skipTaskbar: true, hasShadow: false,
    resizable: false, movable: false, minimizable: false, maximizable: false, fullscreenable: false,
    backgroundColor: '#00000000', show: false, alwaysOnTop: true, thickFrame: false,
    webPreferences: { contextIsolation: true, nodeIntegration: false, backgroundThrottling: false },
  });
  konfetiWin.setAlwaysOnTop(true, 'screen-saver');
  konfetiWin.setIgnoreMouseEvents(true);
  const cx = Math.round(b.x + b.width / 2 - db.x), cy = Math.round(b.y + b.height * 0.4 - db.y);
  konfetiWin.loadURL(`kedi://local/app/konfeti.html#${cx},${cy}`);
  konfetiWin.once('ready-to-show', () => konfetiWin && !konfetiWin.isDestroyed() && konfetiWin.showInactive());
  const bu = konfetiWin;
  setTimeout(() => { if (bu && !bu.isDestroyed()) bu.destroy(); if (konfetiWin === bu) konfetiWin = null; }, 6500);
});

ipcMain.handle('klipler', () => klipleriTara());
ipcMain.handle('ayarlar', () => ({ ses: cfg.ses, butonlar: cfg.butonlar }));

// ---------------------------------------------------------------- tray menu
function otomatikBaslat(acik) {
  if (!app.isPackaged) return;
  try { app.setLoginItemSettings({ openAtLogin: acik, path: process.execPath }); } catch {}
}

function menuyuKur() {
  if (!tray) return;
  const gorunur = win && win.isVisible();
  const radyo = (ad, deger) => ({ label: ad, type: 'radio', checked: cfg.boyut === deger, click: () => boyutDegistir(deger) });
  const menu = Menu.buildFromTemplate([
    { label: gorunur ? 'Kediyi gizle' : 'Kediyi göster', click: () => { if (!win) return; if (win.isVisible()) win.hide(); else { win.showInactive(); win.moveTop(); } } },
    { label: 'Kediyi öne getir', click: () => { if (win) { win.showInactive(); win.moveTop(); } } },
    { type: 'separator' },
    { label: 'Boyut', submenu: [radyo('Küçük', 'kucuk'), radyo('Orta', 'orta'), radyo('Büyük', 'buyuk'), radyo('Çok büyük', 'cok_buyuk')] },
    { label: 'Her zaman en üstte', type: 'checkbox', checked: cfg.ustte, click: (mi) => {
      cfg.ustte = mi.checked; ayarYaz(); if (win) win.setAlwaysOnTop(cfg.ustte, 'floating'); } },
    { label: 'Ses', type: 'checkbox', checked: cfg.ses, click: (mi) => { cfg.ses = mi.checked; ayarYaz(); ayarlariGonder(); } },
    { label: 'Butonlar', submenu: [
      { label: 'Her zaman görünsün', type: 'radio', checked: cfg.butonlar === 'her_zaman', click: () => { cfg.butonlar = 'her_zaman'; ayarYaz(); ayarlariGonder(); } },
      { label: 'Sadece fare yaklaşınca', type: 'radio', checked: cfg.butonlar === 'yaklasinca', click: () => { cfg.butonlar = 'yaklasinca'; ayarYaz(); ayarlariGonder(); } },
    ] },
    { label: 'Bilgisayar açılınca başlasın', type: 'checkbox', checked: cfg.otomatik, click: (mi) => { cfg.otomatik = mi.checked; ayarYaz(); otomatikBaslat(cfg.otomatik); } },
    { type: 'separator' },
    { label: 'Konumu sıfırla', click: () => {
      if (!win) return; const b = win.getBounds(); const p = varsayilanKonum(b.width, b.height);
      win.setBounds({ ...p, width: b.width, height: b.height }); win.showInactive(); konumuKaydet(); } },
    { label: 'Videolar klasörünü aç', click: () => shell.openPath(VIDEO_DIR) },
    { type: 'separator' },
    { label: 'Çıkış', click: () => app.quit() },
  ]);
  tray.setContextMenu(menu);
}

function tepsiyiKur() {
  let img = nativeImage.createFromPath(TRAY_ICON);
  if (img.isEmpty()) img = nativeImage.createFromPath(ICON).resize({ width: 32, height: 32 });
  tray = new Tray(img);
  tray.setToolTip('Kedi');
  tray.on('click', () => { if (win) { win.showInactive(); win.moveTop(); } });
  menuyuKur();
}

// ---------------------------------------------------------------- start
if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on('second-instance', () => { if (win) { win.showInactive(); win.moveTop(); } });
  app.whenReady().then(() => {
    CFG_FILE = path.join(app.getPath('userData'), 'ayarlar.json');
    ayarOku();
    if (cfg.ilk) { cfg.ilk = false; ayarYaz(); }
    otomatikBaslat(cfg.otomatik);   // refresh the path on every launch in case the folder moved
    protokoluKur();
    pencereOlustur();
    tepsiyiKur();
    yakinlikTakibi();
    screen.on('display-removed', tumEkranlaraSigdir);
    screen.on('display-metrics-changed', tumEkranlaraSigdir);
  });
  app.on('window-all-closed', () => { /* keep living in the tray */ });
  app.on('before-quit', () => { clearInterval(yakinlikZ); if (surukle) clearInterval(surukle.t); });
}
