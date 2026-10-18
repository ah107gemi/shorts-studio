// ============================================
// Shorts Studio — Main Application Module
// ============================================

// --- API Helper ---
export function getApiBase() {
    const custom = localStorage.getItem('shorts_studio_backend_url');
    if (custom) return custom.replace(/\/+$/, '');
    if (window.location.hostname.includes('github.io')) {
        return 'http://localhost:8000/api/v1';
    }
    return '/api/v1';
}

export async function api(endpoint, options = {}) {
    const base = getApiBase();
    const url = `${base}${endpoint}`;
    const config = {
        headers: { 'Content-Type': 'application/json', ...options.headers },
        ...options,
    };
    if (config.body && typeof config.body === 'object' && !(config.body instanceof FormData)) {
        config.body = JSON.stringify(config.body);
    }
    if (config.body instanceof FormData) {
        delete config.headers['Content-Type'];
    }
    try {
        const res = await fetch(url, config);
        const text = await res.text();
        let data;
        try { data = JSON.parse(text); } catch { data = text; }
        if (!res.ok) {
            const msg = data?.detail || data?.message || `Request failed (${res.status})`;
            throw new Error(msg);
        }
        return data;
    } catch (err) {
        if (err.name === 'TypeError' && err.message.includes('fetch')) {
            throw new Error(`Cannot reach the server at ${base}. Ensure local backend is running (http://localhost:8000).`);
        }
        throw err;
    }
}

// --- Toast Notification System ---
let toastCounter = 0;

export function showToast(type, title, message = '', duration = 4000) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const id = `toast-${++toastCounter}`;
    const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.id = id;
    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || 'ℹ️'}</span>
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            ${message ? `<div class="toast-message">${message}</div>` : ''}
        </div>
        <button class="toast-close" onclick="this.closest('.toast').remove()">&times;</button>
    `;
    container.appendChild(toast);
    if (duration > 0) {
        setTimeout(() => {
            toast.classList.add('removing');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
    return id;
}

// --- Modal System ---
let modalResolve = null;

export function showModal(title, bodyHtml, footerHtml = '') {
    const overlay = document.getElementById('modal-overlay');
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-body').innerHTML = bodyHtml;
    document.getElementById('modal-footer').innerHTML = footerHtml;
    overlay.classList.add('visible');
}

export function hideModal() {
    document.getElementById('modal-overlay').classList.remove('visible');
    if (modalResolve) {
        modalResolve(false);
        modalResolve = null;
    }
}

export function confirmModal(title, message) {
    return new Promise((resolve) => {
        modalResolve = resolve;
        showModal(title, `<p>${message}</p>`,
            `<button class="btn btn-secondary" id="modal-cancel-btn">Cancel</button>
             <button class="btn btn-primary" id="modal-confirm-btn">Confirm</button>`
        );
        setTimeout(() => {
            document.getElementById('modal-cancel-btn')?.addEventListener('click', () => {
                hideModal();
                resolve(false);
                modalResolve = null;
            });
            document.getElementById('modal-confirm-btn')?.addEventListener('click', () => {
                hideModal();
                resolve(true);
                modalResolve = null;
            });
        }, 0);
    });
}

// --- State Management ---
export const state = {
    currentPage: 'dashboard',
    currentProject: null,
    projects: [],
    _listeners: [],
    set(key, value) {
        this[key] = value;
        this._listeners.forEach(fn => fn(key, value));
    },
    onChange(fn) {
        this._listeners.push(fn);
    }
};

// --- Format Helpers ---
export function formatDate(dateStr) {
    if (!dateStr) return '—';
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export function formatDateTime(dateStr) {
    if (!dateStr) return '—';
    const d = new Date(dateStr);
    return d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export function formatDuration(seconds) {
    if (seconds == null) return '—';
    const s = Math.round(seconds);
    if (s < 60) return `${s}s`;
    const m = Math.floor(s / 60);
    const rem = s % 60;
    return rem ? `${m}m ${rem}s` : `${m}m`;
}

export function formatFileSize(bytes) {
    if (bytes == null) return '—';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

export function statusBadge(status) {
    const s = (status || 'draft').toLowerCase();
    const labels = {
        draft: 'Draft', production: 'Production', rendering: 'Rendering',
        completed: 'Completed', failed: 'Failed', active: 'Active',
        pending: 'Pending', processing: 'Processing', queued: 'Queued',
    };
    const cls = {
        draft: 'draft', production: 'production', rendering: 'rendering',
        completed: 'completed', failed: 'failed', active: 'active',
        pending: 'draft', processing: 'rendering', queued: 'draft',
    };
    return `<span class="badge badge-${cls[s] || 'draft'}">${labels[s] || status}</span>`;
}

export function escapeHtml(str) {
    if (!str) return '';
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}

export function truncate(str, len = 80) {
    if (!str) return '';
    return str.length > len ? str.substring(0, len) + '…' : str;
}

// --- Router ---
const pageModules = {};

async function loadPage(pageName) {
    const container = document.getElementById('page-container');

    // Update nav
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.page === pageName);
    });

    // Show loading
    container.innerHTML = `<div class="loading-overlay"><div class="spinner spinner-lg"></div><span>Loading...</span></div>`;

    try {
        if (!pageModules[pageName]) {
            const pageUrl = new URL(`./pages/${pageName}.js`, import.meta.url).href;
            pageModules[pageName] = await import(pageUrl);
        }
        const mod = pageModules[pageName];
        container.innerHTML = await mod.render();
        if (mod.init) {
            await mod.init();
        }
        state.set('currentPage', pageName);
    } catch (err) {
        console.error(`Failed to load page "${pageName}":`, err);
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <h3>Page Load Error</h3>
                <p>Could not load the "${pageName}" page. ${escapeHtml(err.message)}</p>
                <button class="btn btn-primary" onclick="window.__navigateTo('dashboard')">Go to Dashboard</button>
            </div>
        `;
    }
}

function getPageFromHash() {
    const raw = (window.location.hash || '').replace(/^#\/?/, '').trim();
    return raw || 'dashboard';
}

export function navigateTo(pageName) {
    if (window.location.hash !== `#${pageName}`) {
        window.location.hash = pageName;
    } else {
        loadPage(pageName);
    }
}

// Expose for inline onclick fallback
window.__navigateTo = navigateTo;

// --- Initialization ---
function init() {
    // Sidebar nav clicks
    document.getElementById('sidebar-nav').addEventListener('click', (e) => {
        const navItem = e.target.closest('.nav-item');
        if (!navItem) return;
        e.preventDefault();
        const page = navItem.dataset.page;
        if (page) navigateTo(page);
    });

    // Hash change listener for browser back/forward and direct links
    window.addEventListener('hashchange', () => {
        loadPage(getPageFromHash());
    });

    // Modal close
    document.getElementById('modal-close').addEventListener('click', hideModal);
    document.getElementById('modal-overlay').addEventListener('click', (e) => {
        if (e.target === e.currentTarget) hideModal();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') hideModal();
    });

    // Load page from URL hash or default to dashboard
    loadPage(getPageFromHash());
}

document.addEventListener('DOMContentLoaded', init);
