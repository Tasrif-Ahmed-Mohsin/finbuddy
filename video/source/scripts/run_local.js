// Start a local Bluefin server (fresh sandbox, scratch audit log), run the story capture against it, then stop it.
const { spawn, execFileSync } = require('child_process');
const path = require('path');
const S = process.argv[2];
const env = { ...process.env, SATHI_WEB_DIR: path.join(S, 'vid', 'webdist'), SATHI_AUDIT_PATH: path.join(S, 'vid', 'local_audit.jsonl'),
  SATHI_PASSKEY_REPLACE_OLDEST: '1', WHATSAPP_MODE: 'off', SATHI_FX_MODE: 'live', PYTHONUNBUFFERED: '1' };
const py = 'E:/chinahack/backend/.venv/Scripts/python.exe';
const srv = spawn(py, ['-m', 'uvicorn', 'app.web:site', '--host', '127.0.0.1', '--port', '8765'], { cwd: 'E:/chinahack/backend', env });
srv.stderr.on('data', (d) => { const t = String(d); if (/error|Traceback/i.test(t)) process.stderr.write('[srv] ' + t); });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
(async () => {
  for (let i = 0; i < 60; i++) { try { const r = await fetch('http://127.0.0.1:8765/api/health'); if (r.ok) break; } catch {} await sleep(1000); }
  try {
    execFileSync('node', ['capture_hi.js', 'shots', 'local'], { stdio: 'inherit', cwd: path.join(S, 'vid'), env: process.env });
  } finally { srv.kill(); }
})();
