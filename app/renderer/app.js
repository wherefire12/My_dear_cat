'use strict';
/* Desktop cat — player
 * Reads the files in videolar/<folder>/:
 *   bosta       → idle loops, played continuously in random order
 *   yaklasinca  → when the mouse comes close to the cat
 *   sevme       → the Pet button and clicking the cat (random pick)
 *   mama, temizle, parti → the Feed, Clean and Party buttons
 * .webm = transparent cat, .mp4/.mov = shown as a framed card.
 * (Identifiers are Turkish: the app was first made for a Turkish user.)
 */
const api = window.kedi;
const sahne = document.getElementById('sahne');
const kalpKutusu = document.getElementById('kalpler');
const katmanlar = [...document.querySelectorAll('.katman')].map(el => ({ el, v: el.querySelector('video') }));
const butonlar = [...document.querySelectorAll('.btn')];

let K = {};                       // folder → list of clips
let A = { ses: true, butonlar: 'her_zaman' };
let aktif = -1;                   // visible layer
let mod = 'bosta';                // bosta | yaklasinca | <action>
let token = 0;
let bostaZ = null;
let eylemBas = 0;
let sonYakin = 0;
const sonKlip = {};

const rnd = (a) => a[Math.floor(Math.random() * a.length)];
function sec(klasor) {
  const l = K[klasor] || [];
  if (!l.length) return null;
  let c = rnd(l);
  if (l.length > 1) while (c.url === sonKlip[klasor]) c = rnd(l);
  sonKlip[klasor] = c.url;
  return c;
}

// ------------------------------------------------------------------ layout
function yerlestir(k) {
  const v = k.v, vw = v.videoWidth, vh = v.videoHeight;
  if (!vw || !vh) return;
  const kart = k.el.classList.contains('kart');
  const SW = sahne.clientWidth, SH = sahne.clientHeight;
  const maxW = kart ? SW - 40 : SW, maxH = kart ? SH - 24 : SH;
  const s = Math.min(maxW / vw, maxH / vh);
  v.style.width = Math.round(vw * s) + 'px';
  v.style.height = Math.round(vh * s) + 'px';
}

// ------------------------------------------------------------------ playback
function hazirBekle(v, t) {
  return new Promise((res) => {
    let bitti = false;
    const son = (ok) => { if (bitti) return; bitti = true; v.removeEventListener('canplay', a); v.removeEventListener('error', b); clearTimeout(z); res(ok); };
    const a = () => son(true), b = () => son(false);
    v.addEventListener('canplay', a); v.addEventListener('error', b);
    const z = setTimeout(() => son(v.readyState >= 2), 4000);
    if (v.readyState >= 3) son(true);
  });
}

function sesiUygula(k) {
  if (!k) return;
  k.v.muted = !A.ses;
  k.v.volume = 0.9;
}

async function oynat(klip, dongu, bitince) {
  if (!klip) return;
  const t = ++token;
  const hi = aktif === 0 ? 1 : 0;
  const k = katmanlar[hi], v = k.v;
  v.onended = null;
  v.pause();
  k.el.classList.toggle('kart', !!klip.kart);
  v.loop = !!dongu;
  sesiUygula(k);
  v.src = klip.url;
  v.load();
  const ok = await hazirBekle(v, t);
  if (t !== token) return;                 // something else was requested meanwhile
  if (!ok) { if (bitince) bitince(); return; }
  yerlestir(k);
  v.onended = () => { if (t === token && bitince) bitince(); };
  try { await v.play(); } catch { v.muted = true; try { await v.play(); } catch {} }
  if (t !== token) return;
  const eski = katmanlar[aktif];
  k.el.classList.add('gor');
  aktif = hi;
  if (eski && eski !== k) {
    eski.el.classList.remove('gor');
    setTimeout(() => {
      if (katmanlar[aktif] === eski) return;
      eski.v.pause(); eski.v.onended = null; eski.v.removeAttribute('src'); eski.v.load();
    }, 450);
  }
}

function aktifButon(ad) {
  butonlar.forEach(b => b.classList.toggle('aktif', b.dataset.eylem === ad));
}

function bosta() {
  clearTimeout(bostaZ);
  mod = 'bosta';
  aktifButon(null);
  const k = sec('bosta');
  if (!k) return;
  oynat(k, true);
  bostaZ = setTimeout(bosta, 25000 + Math.random() * 25000);   // switch to another pose after a while
}

function eylem(ad) {
  const k = sec(ad);
  if (!k) return;
  clearTimeout(bostaZ);
  mod = ad; eylemBas = Date.now();
  aktifButon(ad);
  if (ad === 'parti') api.parti();
  if (ad === 'sevme') kalpler();
  oynat(k, false, bosta);
}

function yaklasti() {
  if (mod !== 'bosta' || Date.now() - sonYakin < 30000) return;
  const k = sec('yaklasinca');
  if (!k) return;
  sonYakin = Date.now();
  clearTimeout(bostaZ);
  mod = 'yaklasinca';
  oynat(k, false, bosta);
}

function kediyeTiklandi() {
  if (mod !== 'bosta' && mod !== 'yaklasinca' && Date.now() - eylemBas < 1200) return;
  eylem('sevme');
}

// ------------------------------------------------------------------ hearts
const KALP = '<svg viewBox="0 0 24 24"><path d="M12 21s-7.5-4.6-9.6-9.2C.9 8.4 3 4.5 6.7 4.5c2.1 0 3.6 1.2 4.3 2.5.7-1.3 2.2-2.5 4.3-2.5 3.7 0 5.8 3.9 4.3 7.3C19.5 16.4 12 21 12 21z"/></svg>';
function kalpler() {
  for (let i = 0; i < 8; i++) {
    const h = document.createElement('div');
    h.className = 'kalp';
    h.innerHTML = KALP;
    h.style.left = (18 + Math.random() * 64) + '%';
    h.style.top = (22 + Math.random() * 40) + '%';
    h.style.animationDelay = (i * 0.16) + 's';
    const s = 0.7 + Math.random() * 0.6;
    h.style.width = h.style.height = (26 * s) + 'px';
    h.style.setProperty('--dx', (Math.random() * 50 - 25) + 'px');
    h.style.setProperty('--r', (Math.random() * 40 - 20) + 'deg');
    kalpKutusu.appendChild(h);
    setTimeout(() => h.remove(), 3200 + i * 160);
  }
}

// ------------------------------------------------------------------ let clicks pass through transparent pixels
const tuval = document.createElement('canvas');
tuval.width = tuval.height = 9;
const ctx = tuval.getContext('2d', { willReadFrequently: true });

function kediUstunde(x, y) {
  const k = katmanlar[aktif];
  if (!k || !k.el.classList.contains('gor')) return false;
  const r = k.v.getBoundingClientRect();
  if (x < r.left || x > r.right || y < r.top || y > r.bottom) return false;
  if (k.el.classList.contains('kart')) return true;
  const vw = k.v.videoWidth, vh = k.v.videoHeight;
  if (!vw) return false;
  const px = (x - r.left) / r.width * vw, py = (y - r.top) / r.height * vh;
  const rad = Math.max(3, (vw / r.width) * 5);
  try {
    ctx.clearRect(0, 0, 9, 9);
    ctx.drawImage(k.v, px - rad, py - rad, rad * 2, rad * 2, 0, 0, 9, 9);
    const d = ctx.getImageData(0, 0, 9, 9).data;
    for (let i = 3; i < d.length; i += 4) if (d[i] > 50) return true;
    return false;
  } catch { return true; }
}
function etkilesimli(x, y) {
  const el = document.elementFromPoint(x, y);
  if (el && el.closest('.btn')) return 'buton';
  if (y < sahne.clientHeight && kediUstunde(x, y)) return 'kedi';
  return null;
}

let fare = null, gecirgen = true, surukleniyor = false, bekleyen = false, yakinZ = null;
function degerlendir() {
  bekleyen = false;
  if (surukleniyor) return;
  const hedef = fare ? etkilesimli(fare.x, fare.y) : null;
  const gecsin = !hedef;
  if (gecsin !== gecirgen) { gecirgen = gecsin; api.fareGecsin(gecsin); }
  document.body.classList.toggle('kedi-ustunde', hedef === 'kedi');
}
function fareYakin() {
  document.body.classList.add('fare-yakin');
  clearTimeout(yakinZ);
  yakinZ = setTimeout(() => document.body.classList.remove('fare-yakin'), 3500);
}
document.addEventListener('mousemove', (e) => {
  fare = { x: e.clientX, y: e.clientY };
  fareYakin();
  if (!bekleyen) { bekleyen = true; requestAnimationFrame(degerlendir); }
});
document.addEventListener('mouseleave', () => { fare = null; degerlendir(); });
setInterval(() => { if (fare) degerlendir(); }, 250);   // in case the cat moves out from under the cursor

// ------------------------------------------------------------------ dragging + clicking
sahne.addEventListener('pointerdown', (e) => {
  if (e.button !== 0 || surukleniyor) return;
  if (etkilesimli(e.clientX, e.clientY) !== 'kedi') return;
  e.preventDefault();
  surukleniyor = true;
  document.body.classList.add('surukleniyor');
  try { sahne.setPointerCapture(e.pointerId); } catch {}
  api.surukleBasla();
});
let bitiriliyor = false;
async function surukleBitti(e) {
  if (!surukleniyor || bitiriliyor) return;
  bitiriliyor = true;
  try { sahne.releasePointerCapture(e.pointerId); } catch {}
  let moved = true;
  try { ({ moved } = await api.surukleBitir()); } catch {}
  surukleniyor = false; bitiriliyor = false;
  document.body.classList.remove('surukleniyor');
  if (!moved) kediyeTiklandi();
  degerlendir();
}
sahne.addEventListener('pointerup', surukleBitti);
sahne.addEventListener('pointercancel', surukleBitti);
sahne.addEventListener('lostpointercapture', surukleBitti);

butonlar.forEach(b => b.addEventListener('click', () => eylem(b.dataset.eylem)));

// ------------------------------------------------------------------ watchdog: don't get stuck after being hidden
setInterval(() => {
  if (document.hidden) return;
  const k = katmanlar[aktif];
  if (!k || !k.v.src) return;
  if (k.v.ended) { if (mod !== 'bosta') bosta(); else if (k.v.loop) k.v.play().catch(() => {}); }
  else if (k.v.paused) k.v.play().catch(() => {});
}, 1500);
document.addEventListener('visibilitychange', () => {
  const k = katmanlar[aktif];
  if (!k) return;
  if (document.hidden) k.v.pause();
  else if (k.v.ended && mod !== 'bosta') bosta();
  else k.v.play().catch(() => {});
});

// ------------------------------------------------------------------ startup
function ayarlariUygula(a) {
  A = { ...A, ...a };
  document.body.classList.toggle('bar-otomatik', A.butonlar === 'yaklasinca');
  katmanlar.forEach(sesiUygula);
}
api.onAyarlar(ayarlariUygula);
api.onYakin(() => { fareYakin(); yaklasti(); });

(async () => {
  const [k, a] = await Promise.all([api.klipler(), api.ayarlar()]);
  K = k || {};
  ayarlariUygula(a || {});
  butonlar.forEach(b => { b.hidden = !(K[b.dataset.eylem] || []).length; });
  bosta();
})();
