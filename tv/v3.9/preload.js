const { contextBridge, ipcRenderer } = require('electron');
const inv = (c, ...a) => ipcRenderer.invoke(c, ...a);
contextBridge.exposeInMainWorld('rene', {
  qwen: a => inv('qwen', a), icy: u => inv('icy', u), gpu: () => inv('gpu'),
  logiciels: () => inv('logiciels'), lancer: (qui, arg) => inv('lancer', qui, arg),
  rec: { start: o => inv('rec-start', o), stop: id => inv('rec-stop', id), finie: cb => ipcRenderer.on('rec-fin', (_e, id) => cb(id)) },
  k7: { liste: () => inv('k7-liste'), dossier: () => inv('k7-dossier'), effacer: f => inv('k7-effacer', f) },
  eveil: g => inv('garder-eveil', g)
});
