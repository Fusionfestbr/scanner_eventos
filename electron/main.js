const { app, BrowserWindow, shell } = require('electron');
const path = require('path');
const { spawn, execSync } = require('child_process');
const fs = require('fs');
const http = require('http');

let mainWindow;
let flaskProcess;
let pythonProcess = null;
let LOG_FILE = null;

const FLASK_PORT = 5000;

function killProcessTree(pid) {
    // O Flask sobe via shell (cmd.exe) e o "python" do PATH pode ser um alias
    // que cria outro filho — .kill() mata só o pai e deixa o Python órfão
    // escutando a porta com código antigo. taskkill /T encerra a árvore toda.
    if (!pid) return;
    try {
        execSync(`taskkill /F /T /PID ${pid}`, { stdio: 'ignore' });
        log(`Árvore do processo ${pid} encerrada`);
    } catch (e) { /* processo já não existe */ }
}

function killPortOwner(port) {
    // Antes de subir o Flask, encerra qualquer órfão de sessão anterior
    // que esteja escutando a porta — senão a janela nova conecta num
    // servidor antigo e o usuário vê a interface desatualizada.
    try {
        const out = execSync(`netstat -ano -p tcp | findstr ":${port} "`, { shell: true }).toString();
        const pids = new Set();
        out.split(/\r?\n/).forEach(line => {
            if (line.toUpperCase().includes('LISTENING')) {
                const m = line.trim().match(/(\d+)\s*$/);
                if (m) pids.add(m[1]);
            }
        });
        pids.forEach(pid => {
            log(`Porta ${port} ocupada por PID ${pid} — encerrando órfão antes de iniciar`);
            killProcessTree(pid);
        });
    } catch (e) { /* porta livre: findstr não encontrou nada */ }
}

function getLogFile() {
    if (!LOG_FILE) {
        try {
            const userDataPath = app.isPackaged 
                ? path.dirname(process.execPath)
                : path.join(__dirname, '..');
            LOG_FILE = path.join(userDataPath, 'scanner.log');
        } catch (e) {
            LOG_FILE = path.join(process.cwd(), 'scanner.log');
        }
    }
    return LOG_FILE;
}

function log(message) {
    const timestamp = new Date().toISOString();
    const logMessage = `[${timestamp}] ${message}\n`;
    
    console.log(logMessage.trim());
    
    try {
        const logFile = getLogFile();
        fs.appendFileSync(logFile, logMessage);
    } catch (e) {
        console.error('Failed to write log:', e);
    }
}

function getAppPaths() {
    try {
        const isPackaged = app.isPackaged;
        
        if (isPackaged) {
            const appDir = path.dirname(process.execPath);
            const resourcesDir = app.isPackaged ? process.resourcesPath : path.join(__dirname, '..', 'resources');
            
            let flaskServer = path.join(resourcesDir, 'flask_server.py');
            
            if (!fs.existsSync(flaskServer)) {
                flaskServer = path.join(appDir, 'flask_server.py');
            }
            
            return {
                appDir: appDir,
                resourcesDir: resourcesDir,
                flaskServer: flaskServer,
                dataDir: path.join(resourcesDir, 'data'),
                dashboardDir: path.join(resourcesDir, 'dashboard')
            };
        } else {
            const projectRoot = path.join(__dirname, '..');
            return {
                appDir: projectRoot,
                resourcesDir: path.join(projectRoot, 'resources'),
                flaskServer: path.join(projectRoot, 'flask_server.py'),
                dataDir: path.join(projectRoot, 'data'),
                dashboardDir: path.join(projectRoot, 'dashboard')
            };
        }
    } catch (e) {
        const projectRoot = path.join(__dirname, '..');
        return {
            appDir: projectRoot,
            resourcesDir: path.join(projectRoot, 'resources'),
            flaskServer: path.join(projectRoot, 'flask_server.py'),
            dataDir: path.join(projectRoot, 'data'),
            dashboardDir: path.join(projectRoot, 'dashboard')
        };
    }
}

function findPython() {
    return new Promise((resolve) => {
        const candidates = [
            'python',
            'python3',
            'py',
            'C:\\Python312\\python.exe',
            'C:\\Python311\\python.exe',
            'C:\\Python310\\python.exe',
            'C:\\Python39\\python.exe',
            'C:\\Python38\\python.exe',
            path.join(process.env.LOCALAPPDATA || '', 'Programs', 'Python', 'Python312', 'python.exe'),
            path.join(process.env.LOCALAPPDATA || '', 'Programs', 'Python', 'Python311', 'python.exe'),
            path.join(process.env.LOCALAPPDATA || '', 'Programs', 'Python', 'Python310', 'python.exe'),
            'C:\\Users\\' + (process.env.USERNAME || 'User') + '\\AppData\\Local\\Programs\\Python\\Python312\\python.exe'
        ];

        let index = 0;

        const tryNext = () => {
            if (index >= candidates.length) {
                log('Python não encontrado em nenhuma localização');
                resolve(null);
                return;
            }

            const candidate = candidates[index];
            index++;

            log(`Tentando Python: ${candidate}`);

            const proc = spawn(candidate, ['--version'], { shell: true });
            
            proc.on('error', () => {
                tryNext();
            });

            proc.on('close', (code) => {
                if (code === 0) {
                    log(`Python encontrado: ${candidate}`);
                    resolve(candidate);
                } else {
                    tryNext();
                }
            });

            setTimeout(() => {
                try { proc.kill(); } catch (e) {}
                tryNext();
            }, 2000);
        };

        tryNext();
    });
}

function checkFlaskServer(flaskPath) {
    const paths = getAppPaths();
    
    if (fs.existsSync(flaskPath)) {
        log(`flask_server.py encontrado em: ${flaskPath}`);
        return true;
    }

    const alternativePaths = [
        paths.flaskServer,
        path.join(paths.appDir, 'flask_server.py'),
        path.join(__dirname, '..', 'flask_server.py')
    ];

    for (const altPath of alternativePaths) {
        if (fs.existsSync(altPath)) {
            log(`flask_server.py encontrado em (alternativo): ${altPath}`);
            return true;
        }
    }

    log('flask_server.py NÃO encontrado em nenhuma localização');
    return false;
}

function startFlask(pythonCmd, flaskPath) {
    return new Promise((resolve, reject) => {
        log(`Iniciando Flask com: ${pythonCmd} "${flaskPath}"`);

        const flaskDir = path.dirname(flaskPath);
        const parentDir = path.join(flaskDir, '..');
        const pythonPath = process.env.PYTHONPATH || '';
        const newPythonPath = pythonPath ? `${parentDir};${pythonPath}` : parentDir;

        log(`PythonPath: ${newPythonPath}`);

        pythonProcess = spawn(pythonCmd, [flaskPath], {
            cwd: parentDir,
            shell: true,
            env: {
                ...process.env,
                PYTHONIOENCODING: 'utf-8',
                PYTHONUNBUFFERED: '1',
                PYTHONPATH: newPythonPath
            },
            stdio: ['ignore', 'pipe', 'pipe']
        });

        let outputData = '';
        let errorData = '';

        pythonProcess.stdout.on('data', (data) => {
            const text = data.toString();
            outputData += text;
            log(`[Flask stdout] ${text.trim()}`);
        });

        pythonProcess.stderr.on('data', (data) => {
            const text = data.toString();
            errorData += text;
            log(`[Flask stderr] ${text.trim()}`);
        });

        pythonProcess.on('error', (err) => {
            log(`[Flask erro] ${err.message}`);
            reject(err);
        });

        pythonProcess.on('close', (code) => {
            log(`[Flask fechado] código: ${code}`);
            if (code !== 0 && code !== null) {
                log(`[Flask erro saida] ${errorData}`);
            }
        });

        setTimeout(() => {
            resolve(true);
        }, 3000);
    });
}

function waitForFlask(maxAttempts = 30) {
    return new Promise((resolve) => {
        let attempts = 0;

        const check = () => {
            attempts++;
            log(`Verificando Flask (tentativa ${attempts}/${maxAttempts})...`);

            http.get('http://127.0.0.1:5000/health', (res) => {
                if (res.statusCode === 200) {
                    log('Flask está pronto!');
                    resolve(true);
                } else {
                    if (attempts < maxAttempts) {
                        setTimeout(check, 1000);
                    } else {
                        resolve(false);
                    }
                }
            }).on('error', () => {
                if (attempts < maxAttempts) {
                    setTimeout(check, 1000);
                } else {
                    resolve(false);
                }
            });
        };

        setTimeout(check, 2000);
    });
}

function showError(title, message, details = '') {
    if (!mainWindow) return;
    
    const html = `
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { 
                    font-family: 'Segoe UI', Arial, sans-serif; 
                    padding: 40px; 
                    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
                    color: #fff; 
                    min-height: 100vh;
                }
                .container { max-width: 700px; margin: 0 auto; }
                .error { 
                    background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
                    padding: 30px; 
                    border-radius: 16px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                }
                .error h2 { 
                    margin-top: 0; 
                    margin-bottom: 20px;
                    font-size: 24px;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }
                .error p { 
                    margin-bottom: 15px; 
                    line-height: 1.6;
                }
                .error code { 
                    background: rgba(0,0,0,0.3); 
                    padding: 15px; 
                    display: block; 
                    margin: 15px 0; 
                    white-space: pre-wrap;
                    border-radius: 8px;
                    font-size: 13px;
                }
                .log-btn {
                    background: rgba(255,255,255,0.2);
                    border: none;
                    color: white;
                    padding: 10px 20px;
                    border-radius: 8px;
                    cursor: pointer;
                    margin-top: 15px;
                    font-size: 14px;
                }
                .log-btn:hover { background: rgba(255,255,255,0.3); }
                .info {
                    background: rgba(0,0,0,0.2);
                    padding: 15px;
                    border-radius: 8px;
                    margin-top: 15px;
                }
                .info strong { color: #f39c12; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="error">
                    <h2>⚠️ ${title}</h2>
                    <p>${message}</p>
                    ${details ? `<code>${details}</code>` : ''}
                    <div class="info">
                        <strong>Passos para resolver:</strong><br/><br/>
                        1. Instale Python 3.8+ em <a href="https://www.python.org/downloads/" style="color:#87CEEB;">python.org/downloads</a><br/>
                        2. Marque "Add Python to PATH" durante instalação<br/>
                        3. Abra Prompt de Comando e execute:<br/>
                        <code>pip install -r requirements.txt</code><br/>
                        4. Reinicie o computador<br/>
                        5. Execute este aplicativo novamente
                    </div>
                    <button class="log-btn" onclick="window.electronAPI.openLog()">📄 Ver Log de Erros</button>
                </div>
            </div>
        </body>
        </html>
    `;
    
    mainWindow.loadURL(`data:text/html;charset=UTF-8,${encodeURIComponent(html)}`);
}

function showLoading() {
    if (!mainWindow) return;
    
    const html = `
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { 
                    font-family: 'Segoe UI', Arial, sans-serif; 
                    padding: 40px; 
                    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
                    color: #fff; 
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .container { text-align: center; }
                h2 { 
                    color: #4fc3f7; 
                    margin-bottom: 30px;
                    font-size: 28px;
                }
                .spinner {
                    border: 4px solid rgba(79, 195, 247, 0.2);
                    border-top: 4px solid #4fc3f7;
                    border-radius: 50%;
                    width: 60px;
                    height: 60px;
                    animation: spin 1s linear infinite;
                    margin: 30px auto;
                }
                @keyframes spin { 
                    0% { transform: rotate(0deg); } 
                    100% { transform: rotate(360deg); } 
                }
                p { color: #aaa; margin-top: 20px; }
                .status {
                    background: rgba(0,0,0,0.3);
                    padding: 20px;
                    border-radius: 10px;
                    margin-top: 30px;
                    text-align: left;
                    font-family: monospace;
                    font-size: 12px;
                    max-height: 200px;
                    overflow-y: auto;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>🔍 Scanner Eventos</h2>
                <div class="spinner"></div>
                <p>Iniciando aplicação...</p>
                <div class="status" id="status">Aguarde...</div>
            </div>
            <script>
                let logs = [];
                function addLog(msg) {
                    logs.push(msg);
                    document.getElementById('status').textContent = logs.join('\\n');
                }
                setInterval(() => {
                    fetch('http://127.0.0.1:5000/').catch(() => {});
                }, 3000);
            </script>
        </body>
        </html>
    `;
    
    mainWindow.loadURL(`data:text/html;charset=UTF-8,${encodeURIComponent(html)}`);
}

async function createWindow() {
    log('Criando janela principal...');

    mainWindow = new BrowserWindow({
        width: 1280,
        height: 800,
        title: 'Scanner Eventos',
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js'),
            webviewTag: false
        },
        show: false,
        backgroundColor: '#1a1a2e',
        minWidth: 800,
        minHeight: 600
    });

    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
        log('Janela exibida');
    });

    showLoading();

    mainWindow.webContents.setWindowOpenHandler(({ url }) => {
        shell.openExternal(url);
        return { action: 'deny' };
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });

    mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
        log(`Falha ao carregar: ${errorCode} - ${errorDescription}`);
    });

    try {
        log('Iniciando processo...');
        
        const paths = getAppPaths();
        log(`Modo: ${app.isPackaged ? 'Packaged' : 'Development'}`);
        log(`Caminho app: ${paths.appDir}`);
        log(`Caminho resources: ${paths.resourcesDir}`);

        const pythonCmd = await findPython();
        
        if (!pythonCmd) {
            showError(
                'Python Não Encontrado',
                'O aplicativo precisa do Python instalado para funcionar.',
                'Instale Python 3.8 ou superior em python.org\n\nDurante a instalação, marque "Add Python to PATH"'
            );
            return;
        }

        const flaskPath = paths.flaskServer;
        if (!checkFlaskServer(flaskPath)) {
            showError(
                'Arquivo flask_server.py Não Encontrado',
                'O arquivo necessário para iniciar o servidor não foi encontrado.',
                `Procurado em:\n- ${flaskPath}\n- ${paths.appDir}\n- ${__dirname}`
            );
            return;
        }

        killPortOwner(FLASK_PORT);
        await startFlask(pythonCmd, flaskPath);

        const flaskReady = await waitForFlask(30);

        if (flaskReady) {
            log('Carregando dashboard...');
            mainWindow.loadURL('http://127.0.0.1:5000');
        } else {
            showError(
                'Flask Não Respondeu',
                'O servidor Flask não conseguiu iniciar em tempo hábil.',
                'Isso pode indicar erro nas dependências.\n\nVerifique o log para mais detalhes.'
            );
        }

    } catch (error) {
        log(`Erro durante inicialização: ${error.message}`);
        showError(
            'Erro ao Iniciar',
            error.message,
            error.stack
        );
    }
}

app.whenReady().then(async () => {
    log('=== Scanner Eventos Electron Iniciado ===');
    log(`Versão Electron: ${process.versions.electron}`);
    log(`Versão Node: ${process.versions.node}`);
    log(`Plataforma: ${process.platform}`);
    
    await createWindow();

    app.on('activate', async () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            await createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    log('Janelas fechadas, encerrando...');

    if (pythonProcess) {
        killProcessTree(pythonProcess.pid);
    }
    
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

process.on('exit', () => {
    log('Processo encerrado');
    if (pythonProcess) {
        killProcessTree(pythonProcess.pid);
    }
});