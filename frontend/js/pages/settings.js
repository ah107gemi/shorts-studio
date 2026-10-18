// ============================================
// Settings & Provider Connections Page
// ============================================
import { api, showToast, state, escapeHtml } from '../app.js';

export async function render() {
    return `
        <div class="page-header-row mb-3">
            <div>
                <h1>⚙️ Settings & External Providers</h1>
                <p class="text-secondary">Configure AI engines, Text-to-Speech voices, media APIs, and local system environment</p>
            </div>
            <div class="btn-group">
                <button class="btn btn-secondary" id="settings-refresh-btn">🔄 Refresh All</button>
            </div>
        </div>

        <div class="grid grid-2 gap-3 mb-3">
            <!-- Left: AI & Media Provider Configs -->
            <div class="flex flex-col gap-3">
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">AI & Media Providers</h3>
                        <span class="text-xs text-muted">Modular API Connectors</span>
                    </div>
                    <div class="card-body" id="providers-list-container">
                        <div class="loading-overlay"><div class="spinner"></div><span>Loading providers...</span></div>
                    </div>
                </div>
            </div>

            <!-- Right: System Info & General Settings -->
            <div class="flex flex-col gap-3">
                <!-- System Diagnostics -->
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">System & Media Engine</h3>
                        <span class="badge badge-info" id="sys-ffmpeg-badge">Checking...</span>
                    </div>
                    <div class="card-body" id="system-info-body">
                        <div class="loading-overlay"><div class="spinner"></div></div>
                    </div>
                </div>

                <!-- Video Generation Defaults -->
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">Default Video Pipeline Settings</h3>
                    </div>
                    <div class="card-body">
                        <div class="grid grid-2 gap-2 mb-2">
                            <div class="form-group">
                                <label class="form-label text-xs">Default Width (px)</label>
                                <input id="set-res-w" type="number" class="form-control text-sm" value="1080">
                            </div>
                            <div class="form-group">
                                <label class="form-label text-xs">Default Height (px)</label>
                                <input id="set-res-h" type="number" class="form-control text-sm" value="1920">
                            </div>
                        </div>

                        <div class="grid grid-2 gap-2 mb-3">
                            <div class="form-group">
                                <label class="form-label text-xs">Frame Rate (FPS)</label>
                                <select id="set-fps" class="form-control text-sm">
                                    <option value="30">30 FPS (Recommended)</option>
                                    <option value="60">60 FPS (Smooth)</option>
                                    <option value="24">24 FPS (Cinematic)</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label class="form-label text-xs">Log Verbosity</label>
                                <select id="set-log-level" class="form-control text-sm">
                                    <option value="INFO">INFO</option>
                                    <option value="DEBUG">DEBUG</option>
                                    <option value="WARNING">WARNING</option>
                                    <option value="ERROR">ERROR</option>
                                </select>
                            </div>
                        </div>

                        <button class="btn btn-primary btn-sm w-full" id="save-app-settings-btn">Save Pipeline Defaults</button>
                    </div>
                </div>
            </div>
        </div>
    `;
}

export async function init() {
    document.getElementById('settings-refresh-btn').addEventListener('click', loadAllSettings);
    document.getElementById('save-app-settings-btn').addEventListener('click', saveAppSettings);

    await loadAllSettings();
}

async function loadAllSettings() {
    await Promise.allSettled([loadProviders(), loadSystemInfo(), loadAppSettings()]);
}

async function loadProviders() {
    const container = document.getElementById('providers-list-container');
    try {
        const providers = await api('/settings/providers');
        const defaultProviders = [
            { name: 'openai', label: 'OpenAI (GPT-4o & DALL-E 3)', type: 'LLM & Image Generation', desc: 'Scriptwriting, hook generation, and scene visual prompts.' },
            { name: 'anthropic', label: 'Anthropic (Claude 3.5)', type: 'LLM Scriptwriting', desc: 'Creative storytelling and research briefs.' },
            { name: 'elevenlabs', label: 'ElevenLabs Text-to-Speech', type: 'Voiceover Synthesis', desc: 'Realistic, expressive voiceovers for Shorts.' },
            { name: 'pexels', label: 'Pexels Media API', type: 'Stock Video & Photos', desc: 'Free high-res vertical B-roll footage and backgrounds.' },
            { name: 'pixabay', label: 'Pixabay Media API', type: 'Stock Media & Music', desc: 'Copyright-safe background music and sound effects.' },
        ];

        container.innerHTML = defaultProviders.map(p => {
            const current = (providers || []).find(x => x.provider_name === p.name);
            const isConfigured = current ? current.api_key_set : false;

            return `
                <div class="card p-3 mb-2" style="background: #191924; border: 1px solid var(--border-color);">
                    <div class="flex justify-between items-center mb-1">
                        <div>
                            <strong class="text-sm font-semibold">${escapeHtml(p.label)}</strong>
                            <div class="text-xs text-secondary">${escapeHtml(p.type)}</div>
                        </div>
                        <span class="badge ${isConfigured ? 'badge-success' : 'badge-draft'}">
                            ${isConfigured ? 'Connected' : 'No Key Set'}
                        </span>
                    </div>
                    <p class="text-xs text-muted mb-2">${escapeHtml(p.desc)}</p>
                    <div class="flex items-center gap-2">
                        <input type="password" placeholder="${isConfigured ? '••••••••••••••••' : 'Enter API Key...'}" class="form-control text-xs provider-key-input" data-provider="${p.name}" style="flex: 1;">
                        <button class="btn btn-secondary btn-sm save-key-btn" data-provider="${p.name}">Save</button>
                        <button class="btn btn-ghost btn-sm test-key-btn" data-provider="${p.name}">Test</button>
                    </div>
                </div>
            `;
        }).join('');

        // Attach listeners
        container.querySelectorAll('.save-key-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const name = e.target.dataset.provider;
                const input = container.querySelector(`.provider-key-input[data-provider="${name}"]`);
                const val = input.value.trim();
                if (!val) {
                    showToast('warning', 'Please enter an API key');
                    return;
                }
                try {
                    await api(`/settings/providers/${name}`, {
                        method: 'PUT',
                        body: { api_key: val, is_enabled: true }
                    });
                    input.value = '';
                    input.placeholder = '••••••••••••••••';
                    showToast('success', `${name} key saved`);
                    await loadProviders();
                } catch (err) {
                    showToast('error', 'Failed to save key', err.message);
                }
            });
        });

        container.querySelectorAll('.test-key-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const name = e.target.dataset.provider;
                try {
                    const res = await api(`/settings/providers/${name}/test`, { method: 'POST' });
                    if (res.success) {
                        showToast('success', `${name}: ${res.message}`);
                    } else {
                        showToast('warning', `${name}: ${res.message}`);
                    }
                } catch (err) {
                    showToast('error', 'Test error', err.message);
                }
            });
        });

    } catch (err) {
        container.innerHTML = `<p class="text-sm text-danger">Failed to load provider configurations: ${escapeHtml(err.message)}</p>`;
    }
}

async function loadSystemInfo() {
    const body = document.getElementById('system-info-body');
    const badge = document.getElementById('sys-ffmpeg-badge');
    try {
        const sys = await api('/settings/system');
        const ffmpegOk = sys.ffmpeg_available;

        badge.className = `badge ${ffmpegOk ? 'badge-success' : 'badge-warning'}`;
        badge.textContent = ffmpegOk ? 'FFmpeg Ready' : 'FFmpeg Missing';

        body.innerHTML = `
            <div class="flex flex-col gap-2 text-sm">
                <div class="flex justify-between py-1 border-b">
                    <span class="text-secondary">Python Runtime</span>
                    <strong>v${sys.python_version}</strong>
                </div>
                <div class="flex justify-between py-1 border-b">
                    <span class="text-secondary">Shorts Studio Version</span>
                    <strong>v${sys.app_version}</strong>
                </div>
                <div class="flex justify-between py-1 border-b">
                    <span class="text-secondary">FFmpeg Status</span>
                    <span class="${ffmpegOk ? 'text-success font-semibold' : 'text-warning font-semibold'}">
                        ${ffmpegOk ? 'Installed & Operational' : 'Not Detected in PATH'}
                    </span>
                </div>
                ${sys.ffmpeg_path ? `
                    <div class="flex justify-between py-1 border-b">
                        <span class="text-secondary">FFmpeg Binary</span>
                        <span class="text-xs text-muted truncate" style="max-width: 250px;" title="${escapeHtml(sys.ffmpeg_path)}">${escapeHtml(sys.ffmpeg_path)}</span>
                    </div>
                ` : ''}
                <div class="flex justify-between py-1">
                    <span class="text-secondary">Disk Free Space</span>
                    <span>${sys.disk_free_bytes ? `${Math.round(sys.disk_free_bytes / (1024 * 1024 * 1024))} GB Free` : 'Available'}</span>
                </div>
            </div>
        `;
    } catch (err) {
        body.innerHTML = `<p class="text-sm text-danger">Failed to load system info: ${escapeHtml(err.message)}</p>`;
    }
}

async function loadAppSettings() {
    try {
        const app = await api('/settings/app');
        if (app.default_resolution_w) document.getElementById('set-res-w').value = app.default_resolution_w;
        if (app.default_resolution_h) document.getElementById('set-res-h').value = app.default_resolution_h;
        if (app.default_fps) document.getElementById('set-fps').value = app.default_fps;
        if (app.log_level) document.getElementById('set-log-level').value = app.log_level;
    } catch {
        // use defaults
    }
}

async function saveAppSettings() {
    try {
        await api('/settings/app', {
            method: 'PUT',
            body: {
                default_resolution_w: parseInt(document.getElementById('set-res-w').value, 10) || 1080,
                default_resolution_h: parseInt(document.getElementById('set-res-h').value, 10) || 1920,
                default_fps: parseInt(document.getElementById('set-fps').value, 10) || 30,
                log_level: document.getElementById('set-log-level').value,
            }
        });
        showToast('success', 'Pipeline settings updated');
    } catch (err) {
        showToast('error', 'Failed to save settings', err.message);
    }
}
