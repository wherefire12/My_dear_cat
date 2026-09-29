#!/usr/bin/env bash
# Builds the single-file Windows installer: out/MyDearCat-Setup.exe
# Requires Node.js and NSIS (makensis). On Linux: sudo apt install nsis
set -euo pipefail
cd "$(dirname "$0")/.."
node build/package-win.mjs
rm -rf staging out && mkdir -p staging out
cp -r dist/Kedi-win32-x64/. staging/
cp -r videolar staging/
cp build/README.txt staging/README.txt
(cd build && makensis -V2 installer.nsi)
ls -lh out/MyDearCat-Setup.exe
