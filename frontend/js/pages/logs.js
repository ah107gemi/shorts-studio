// ============================================
// Logs & Diagnostics Page
// ============================================
import { api, showToast, state, escapeHtml } from '../app.js';

let logsData = [];
let autoRefreshTimer = null;

export async function render() {
    return `
        <div class="page-header-row mb-3">
            <div>
                <h1>📋 Logs & Diagnostics</h1>
                <p class="text-secondary">Inspect live application traces, FFmpeg render outputs, background workers, and API diagnostics</p>
            </div>
            <div class="btn-group">
                <button class="btn btn-secondary" id="logs-refresh-btn">🔄 Refresh Logs</button>
                <button class="btn btn-ghost" id="logs-clear-btn">🗑️ Clear View</button>
            </div>
        </div>

        <!-- Filter Controls -->
        <div class="card mb-3">
            <div class="card-body flex items-center justify-between flex-wrap gap-2">
                <div class="flex items-center gap-2">
                    <span class="text-xs font-semibold text-secondary">Filter Level:</span>
                    <button class="btn btn-primary btn-sm log-filter-btn" data-level="ALL">ALL</button>
                    <button class="btn btn-ghost btn-sm log-filter-btn" data-level="INFO">INFO</button>
                    <button class="btn btn-ghost btn-sm log-filter-btn" data-level="WARNING">WARNING</button>
                    <button class="btn btn-ghost btn-sm log-filter-btn text-danger" data-level="ERROR">ERROR</button>
                </div>
                <div class="flex items-center gap-2">
                    <label class="text-xs text-secondary flex items-center gap-1 cursor-pointer">
                        <input type="checkbox" id="logs-auto-refresh-check" checked>
                        <span>Live Stream (every 4s)</span>
                    </label>
                </div>
            </div>
        </div>

        <!-- Log Output Console -->
        <div class="card">
            <div class="card-header flex justify-between items-center">
                <h3 class="card-title">Console Output</h3>
                <span class="text-xs text-muted" id="logs-count-label">0 lines</span>
            </div>
            <div class="card-body p-0">
                <div id="logs-console" style="background: #09090d; color: #d1d5db; font-family: 'Consolas', 'Courier New', monospace; font-size: 0.8rem; line-height: 1.5; padding: 16px; height: 560px; overflow-y: auto; white-space: pre-wrap; word-break: break-all;">
                    <div class="loading-overlay"><div class="spinner"></div><span>Fetching diagnostics...</span></div>
                </div>
            </div>
        </div>
    `;
}

export async function init() {
    document.getElementById('logs-refresh-btn').addEventListener('click', () => fetchLogs());
    document.getElementById('logs-clear-btn').addEventListener('click', () => {
        logsData = [];
        renderConsole();
    });

    document.querySelectorAll('.log-filter-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.log-filter-btn').forEach(b => {
                b.classList.remove('btn-primary');
                b.classList.add('btn-ghost');
            });
            e.target.classList.remove('btn-ghost');
            e.target.classList.add('btn-primary');
            currentFilter = e.target.dataset.level;
            renderConsole();
        });
    });

    const autoCheck = document.getElementById('logs-auto-refresh-check');
    autoCheck.addEventListener('change', (e) => {
        if (e.target.checked) startAutoRefresh();
        else stopAutoRefresh();
    });

    await fetchLogs();
    startAutoRefresh();
}

let currentFilter = 'ALL';

function startAutoRefresh() {
    stopAutoRefresh();
    autoRefreshTimer = setInterval(async () => {
        if (state.currentPage === 'logs') {
            await fetchLogs(false);
        } else {
            stopAutoRefresh();
        }
    }, 4000);
}

function stopAutoRefresh() {
    if (autoRefreshTimer) {
        clearInterval(autoRefreshTimer);
        autoRefreshTimer = null;
    }
}

async function fetchLogs(scroll = true) {
    const consoleEl = document.getElementById('logs-console');
    if (!consoleEl) return;

    try {
        const res = await api('/logs');
        logsData = res.lines || [];
        renderConsole(scroll);
    } catch {
        // Fallback: mock initial diagnostics if backend logs endpoint is booting
        if (logsData.length === 0) {
            logsData = [
                `[INFO] Shorts Studio frontend client initialized`,
                `[INFO] Checking backend connectivity at /api/health...`,
                `[INFO] Background pipeline worker initialized`,
            ];
            renderConsole(scroll);
        }
    }
}

function renderConsole(scroll = true) {
    const consoleEl = document.getElementById('logs-console');
    if (!consoleEl) return;

    let filtered = logsData;
    if (currentFilter !== 'ALL') {
        filtered = logsData.filter(line => line.includes(`| ${currentFilter}`) || line.includes(`[${currentFilter}]`));
    }

    document.getElementById('logs-count-label').textContent = `${filtered.length} entries`;

    if (filtered.length === 0) {
        consoleEl.innerHTML = '<span class="text-muted">No log entries matching filter.</span>';
        return;
    }

    consoleEl.innerHTML = filtered.map(line => {
        let color = '#d1d5db';
        if (line.includes('ERROR') || line.includes('error')) color = '#ff6b6b';
        else if (line.includes('WARNING') || line.includes('warn')) color = '#feca57';
        else if (line.includes('INFO')) color = '#48dbfb';
        else if (line.includes('SUCCESS') || line.includes('completed')) color = '#1dd1a1';

        return `<div style="color: ${color}; padding: 1px 0;">${escapeHtml(line)}</div>`;
    }).join('');

    if (scroll) {
        consoleEl.scrollTop = consoleEl.scrollHeight;
    }
}
