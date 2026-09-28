// Development test only: runs with KEDI_TEST=<output dir>, never packaged.
const fs = require('fs'), path = require('path');
module.exports = (win, app, outDir) => {
  fs.mkdirSync(outDir, { recursive: true });
  const wc = win.webContents;
  wc.on('console-message', (e) => console.log('[renderer]', e.level, e.message));
  wc.on('render-process-gone', (_e, d) => console.log('RENDER GONE', d));
  const bekle = (ms) => new Promise(r => setTimeout(r, ms));
  const js = (s) => wc.executeJavaScript(s, true);
  const cek = async (ad) => {
    const img = await wc.capturePage();
    fs.writeFileSync(path.join(outDir, ad + '.png'), img.toPNG());
    const durum = await js(`(()=>{const k=[...document.querySelectorAll('.katman')].map(e=>({gor:e.classList.contains('gor'),kart:e.classList.contains('kart'),src:(e.querySelector('video').currentSrc||'').split('/').pop(),t:+e.querySelector('video').currentTime.toFixed(2),w:e.querySelector('video').style.width,h:e.querySelector('video').style.height,muted:e.querySelector('video').muted,paused:e.querySelector('video').paused,err:e.querySelector('video').error&&e.querySelector('video').error.code}));return JSON.stringify({mod,k,aktifBtn:[...document.querySelectorAll('.btn.aktif')].map(b=>b.dataset.eylem)})})()`);
    console.log('SHOT', ad, durum);
  };
  wc.once('did-finish-load', async () => {
    try {
      await bekle(2500); await cek('01_bosta');
      await js(`document.querySelector('[data-eylem=sevme]').click()`); await bekle(2500); await cek('02_sevme');
      await js(`document.querySelector('[data-eylem=mama]').click()`); await bekle(2500); await cek('03_mama');
      await js(`document.querySelector('[data-eylem=temizle]').click()`); await bekle(2500); await cek('04_temizle');
      await js(`document.querySelector('[data-eylem=parti]').click()`); await bekle(1500); await cek('05_parti');
      const { BrowserWindow } = require('electron');
      const kw = BrowserWindow.getAllWindows().find(w => w !== win);
      console.log('CONFETTI WINDOW', kw ? JSON.stringify(kw.getBounds()) : 'NONE');
      if (kw) { const im = await kw.webContents.capturePage(); fs.writeFileSync(path.join(outDir, '05b_konfeti.png'), im.toPNG()); }
      await bekle(4000); await cek('06_parti_sonrasi_bosta');
      // proximity
      await js(`sonYakin=0; mod='bosta'`); win.webContents.send('yakin'); await bekle(2000); await cek('07_yaklasinca');
      // hit test: is the middle of the cat opaque?
      const hit = await js(`(()=>{const k=katmanlar[aktif];const r=k.v.getBoundingClientRect();return [etkilesimli(r.left+r.width/2,r.top+r.height*0.6), etkilesimli(3,3), etkilesimli(170,470)]})()`);
      console.log('HIT (middle, corner, button):', hit);
      // does it return to idle when a clip ends? (short clip sevme_buton_3, 7 s)
      await js(`K.sevme=K.sevme.filter(c=>c.ad.includes('buton_3')); eylem('sevme')`); await bekle(8500); await cek('08_eylem_bitti');
      // resize
      win.setBounds({ ...win.getBounds(), width: Math.round(372*1.3), height: Math.round(504*1.3) }); wc.setZoomFactor(1.3);
      await bekle(1500); await cek('09_buyuk');
      console.log('SIZE', JSON.stringify(win.getBounds()));
    } catch (e) { console.log('TEST ERROR', e && e.stack || e); }
    setTimeout(() => app.quit(), 500);
  });
};
