// ============================================
// Project Library Page
// ============================================
import { api, showToast, navigateTo, confirmModal, formatDate, formatDuration, statusBadge, state, escapeHtml, truncate } from '../app.js';

let allProjects = [];
let currentFilter = 'all';
let searchQuery = '';

export async function render() {
    return `
        <div class="page-header">
            <div class="page-header-row">
                <div>
                    <h1>📁 Project Library</h1>
                    <p>Browse and manage all your projects</p>
                </div>
                <button class="btn btn-primary" id="lib-new-project">➕ New Project</button>
            </div>
        </div>

        <!-- Filters -->
        <div class="filter-bar">
            <div class="search-input">
                <input type="text" id="lib-search" placeholder="Search projects...">
            </div>
            <div class="chip-group" id="lib-filters">
                <button class="chip active" data-filter="all">All</button>
                <button class="chip" data-filter="draft">Draft</button>
                <button class="chip" data-filter="production">Production</button>
                <button class="chip" data-filter="rendering">Rendering</button>
                <button class="chip" data-filter="completed">Completed</button>
                <button class="chip" data-filter="failed">Failed</button>
            </div>
        </div>

        <!-- Project Grid -->
        <div class="card-grid" id="lib-projects">
            <div class="loading-overlay" style="grid-column: 1/-1;"><div class="spinner"></div><span>Loading projects...</span></div>
        </div>
    `;
}

export async function init() {
    document.getElementById('lib-new-project').addEventListener('click', () => navigateTo('new-project'));

    // Search
    document.getElementById('lib-search').addEventListener('input', (e) => {
        searchQuery = e.target.value.trim().toLowerCase();
        renderProjects();
    });

    // Filters
    document.getElementById('lib-filters').addEventListener('click', (e) => {
        const chip = e.target.closest('.chip');
        if (!chip) return;
        document.querySelectorAll('#lib-filters .chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        currentFilter = chip.dataset.filter;
        renderProjects();
    });

    await loadProjects();
}

async function loadProjects() {
    try {
        const data = await api('/projects');
        allProjects = Array.isArray(data) ? data : (data.projects || data.items || []);
        renderProjects();
    } catch (err) {
        document.getElementById('lib-projects').innerHTML = `
            <div class="empty-state" style="grid-column:1/-1;">
                <div class="empty-state-icon">⚠️</div>
                <h3>Failed to load projects</h3>
                <p>${escapeHtml(err.message)}</p>
            </div>
        `;
    }
}

function renderProjects() {
    const container = document.getElementById('lib-projects');
    let filtered = allProjects;

    if (currentFilter !== 'all') {
        filtered = filtered.filter(p => (p.status || 'draft').toLowerCase() === currentFilter);
    }

    if (searchQuery) {
        filtered = filtered.filter(p =>
            (p.name || p.topic || '').toLowerCase().includes(searchQuery) ||
            (p.topic || '').toLowerCase().includes(searchQuery)
        );
    }

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="empty-state" style="grid-column:1/-1;">
                <div class="empty-state-icon">📂</div>
                <h3>${allProjects.length === 0 ? 'No projects yet' : 'No matching projects'}</h3>
                <p>${allProjects.length === 0 ? 'Create your first project to get started.' : 'Try adjusting your filters or search.'}</p>
                ${allProjects.length === 0 ? `<button class="btn btn-primary" onclick="window.__navigateTo('new-project')">➕ Create Project</button>` : ''}
            </div>
        `;
        return;
    }

    container.innerHTML = filtered.map(p => {
        const id = p.id || p.project_id;
        return `
        <div class="card project-lib-card" data-id="${id}">
            <div class="scene-card-thumbnail">
                ${p.thumbnail ? `<img src="${p.thumbnail}" alt="">` : '🎬'}
            </div>
            <div class="card-header">
                <span class="card-title truncate" style="flex:1;">${escapeHtml(p.name || p.topic || 'Untitled')}</span>
                ${statusBadge(p.status)}
            </div>
            <div class="card-body">
                <p class="text-sm text-muted truncate">${escapeHtml(truncate(p.topic || '', 80))}</p>
            </div>
            <div class="card-footer">
                <span class="text-xs text-muted">${formatDate(p.updated_at || p.created_at)}</span>
                <div class="btn-group">
                    <button class="btn btn-ghost btn-sm lib-open" data-id="${id}" title="Open">📝</button>
                    <button class="btn btn-ghost btn-sm lib-dup" data-id="${id}" title="Duplicate">📋</button>
                    <button class="btn btn-ghost btn-sm lib-del" data-id="${id}" title="Delete">🗑️</button>
                </div>
            </div>
        </div>
        `;
    }).join('');

    // Event handlers
    container.querySelectorAll('.lib-open').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            state.set('currentProject', btn.dataset.id);
            navigateTo('script-editor');
        });
    });

    container.querySelectorAll('.lib-dup').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            try {
                await api(`/projects/${btn.dataset.id}/duplicate`, { method: 'POST' });
                showToast('success', 'Project Duplicated');
                await loadProjects();
            } catch (err) {
                showToast('error', 'Duplicate Failed', err.message);
            }
        });
    });

    container.querySelectorAll('.lib-del').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const confirmed = await confirmModal('Delete Project', 'Are you sure you want to delete this project? This action cannot be undone.');
            if (!confirmed) return;
            try {
                await api(`/projects/${btn.dataset.id}`, { method: 'DELETE' });
                showToast('success', 'Project Deleted');
                await loadProjects();
            } catch (err) {
                showToast('error', 'Delete Failed', err.message);
            }
        });
    });

    // Click card to open
    container.querySelectorAll('.project-lib-card').forEach(card => {
        card.style.cursor = 'pointer';
        card.addEventListener('click', () => {
            state.set('currentProject', card.dataset.id);
            navigateTo('script-editor');
        });
    });
}
