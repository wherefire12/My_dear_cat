// Packages app/ as a Windows x64 application → dist/Kedi-win32-x64
import { packager } from '@electron/packager';
import fs from 'node:fs';
import path from 'node:path';

const [out] = await packager({
  dir: 'app', out: 'dist', overwrite: true, platform: 'win32', arch: 'x64',
  electronVersion: '44.4.5', name: 'Kedi', executableName: 'Kedi', asar: false, prune: false,
  icon: 'build/icon.ico', appCopyright: 'Hakan',
  win32metadata: { CompanyName: 'Hakan', FileDescription: 'Kedi', ProductName: 'Kedi', InternalName: 'Kedi', OriginalFilename: 'Kedi.exe' },
  ignore: [/test-scenario\.js$/],
});
// keep only the Turkish and English locale files
const loc = path.join(out, 'locales');
for (const f of fs.readdirSync(loc)) if (!['en-US.pak', 'tr.pak'].includes(f)) fs.rmSync(path.join(loc, f));
console.log('Packaged:', out);
