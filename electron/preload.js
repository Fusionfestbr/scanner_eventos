const { contextBridge, ipcRenderer, app } = require('electron');
const fs = require('fs');
const path = require('path');

contextBridge.exposeInMainWorld('electronAPI', {
    openExternal: (url) => require('electron').shell.openExternal(url),
    minimize: () => ipcRenderer.send('window-minimize'),
    maximize: () => ipcRenderer.send('window-maximize'),
    close: () => ipcRenderer.send('window-close'),
    isElectron: true,
    openLog: () => {
        try {
            const userDataPath = app.isPackaged 
                ? path.dirname(process.execPath)
                : path.join(__dirname, '..');
            const logPath = path.join(userDataPath, 'scanner.log');
            
            if (fs.existsSync(logPath)) {
                require('electron').shell.openPath(logPath);
            } else {
                alert('Log não existe ainda. O aplicativo pode não ter iniciado corretamente.');
            }
        } catch (e) {
            alert('Erro ao abrir log: ' + e.message);
        }
    },
    getVersion: () => app.getVersion()
});