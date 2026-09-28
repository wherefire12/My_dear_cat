'use strict';
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('kedi', {
  klipler: () => ipcRenderer.invoke('klipler'),
  ayarlar: () => ipcRenderer.invoke('ayarlar'),
  fareGecsin: (v) => ipcRenderer.send('fare-gecsin', !!v),
  surukleBasla: () => ipcRenderer.send('drag-start'),
  surukleBitir: () => ipcRenderer.invoke('drag-end'),
  parti: () => ipcRenderer.send('parti'),
  onAyarlar: (cb) => ipcRenderer.on('ayarlar', (_e, a) => cb(a)),
  onYakin: (cb) => ipcRenderer.on('yakin', () => cb()),
});
