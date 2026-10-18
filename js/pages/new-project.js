// ============================================
// New Project Page
// ============================================
import { api, showToast, navigateTo, state } from '../app.js';

const NICHES = ['Technology', 'Science', 'History', 'Business', 'Health', 'Education', 'Entertainment', 'Gaming', 'Lifestyle', 'Travel', 'Food', 'Sports', 'News', 'Comedy', 'Motivation', 'Other'];
const TONES = ['Professional', 'Casual', 'Humorous', 'Dramatic', 'Inspirational', 'Educational', 'Storytelling', 'Conversational'];
const STYLES = ['Documentary', 'Tutorial', 'Explainer', 'Narrative', 'List/Listicle', 'News Report', 'Interview', 'Montage', 'Vlog'];
const PLATFORMS = ['YouTube Shorts', 'TikTok', 'Instagram Reels', 'General'];
const VISUAL_STYLES = ['Cinematic', 'Animated', 'Stock Footage', 'Mixed Media', 'Minimalist', 'Vibrant', 'Dark/Moody', 'Retro'];
const LANGUAGES = ['English', 'Spanish', 'French', 'German', 'Portuguese', 'Hindi', 'Japanese', 'Korean', 'Chinese', 'Arabic'];
const CATEGORIES = [
    { label: '📚 Educational', topic: 'Educational explainer video' },
    { label: '💻 Tech', topic: 'Technology review or tutorial' },
    { label: '🏛️ History', topic: 'Fascinating historical event' },
    { label: '📖 Story', topic: 'Compelling short story' },
    { label: '💪 Motivational', topic: 'Motivational and inspiring message' },
    { label: '🎯 General', topic: '' },
];

export async function render() {
    return `
        <div class="page-header">
            <h1>➕ New Project</h1>
            <p>Configure your short video project</p>
        </div>

        <!-- Quick Category Select -->
        <div class="mb-3">
            <label class="form-label">Quick Start Category</label>
            <div class="quick-select" id="category-select">
                ${CATEGORIES.map((c, i) => `
                    <button class="quick-select-btn" data-idx="${i}">${c.label}</button>
                `).join('')}
            </div>
        </div>

        <form id="new-project-form" class="card" style="padding: 24px;">
            <!-- Topic -->
            <div class="form-group">
                <label class="form-label" for="np-topic">Topic / Title *</label>
                <input type="text" id="np-topic" class="form-input" placeholder="What is your video about?" required>
                <span class="form-hint">Describe the main subject of your short video</span>
            </div>

            <div class="form-row">
                <!-- Niche -->
                <div class="form-group">
                    <label class="form-label" for="np-niche">Niche</label>
                    <select id="np-niche" class="form-select">
                        ${NICHES.map(n => `<option value="${n.toLowerCase()}">${n}</option>`).join('')}
                    </select>
                </div>
                <!-- Platform -->
                <div class="form-group">
                    <label class="form-label" for="np-platform">Platform</label>
                    <select id="np-platform" class="form-select">
                        ${PLATFORMS.map(p => `<option value="${p.toLowerCase().replace(/\s+/g, '_')}">${p}</option>`).join('')}
                    </select>
                </div>
                <!-- Language -->
                <div class="form-group">
                    <label class="form-label" for="np-language">Language</label>
                    <select id="np-language" class="form-select">
                        ${LANGUAGES.map(l => `<option value="${l.toLowerCase()}" ${l === 'English' ? 'selected' : ''}>${l}</option>`).join('')}
                    </select>
                </div>
            </div>

            <!-- Target Audience -->
            <div class="form-group">
                <label class="form-label" for="np-audience">Target Audience</label>
                <input type="text" id="np-audience" class="form-input" placeholder="e.g., Young adults interested in tech" value="General audience">
            </div>

            <!-- Duration Slider -->
            <div class="form-group">
                <label class="form-label">Duration: <strong id="np-duration-label">60s</strong></label>
                <input type="range" id="np-duration" class="form-range" min="15" max="180" value="60" step="5">
                <div class="flex justify-between text-xs text-muted mt-1">
                    <span>15s</span><span>60s</span><span>120s</span><span>180s</span>
                </div>
            </div>

            <div class="form-row">
                <!-- Tone -->
                <div class="form-group">
                    <label class="form-label" for="np-tone">Tone</label>
                    <select id="np-tone" class="form-select">
                        ${TONES.map(t => `<option value="${t.toLowerCase()}">${t}</option>`).join('')}
                    </select>
                </div>
                <!-- Style -->
                <div class="form-group">
                    <label class="form-label" for="np-style">Style</label>
                    <select id="np-style" class="form-select">
                        ${STYLES.map(s => `<option value="${s.toLowerCase()}">${s}</option>`).join('')}
                    </select>
                </div>
                <!-- Visual Style -->
                <div class="form-group">
                    <label class="form-label" for="np-visual-style">Visual Style</label>
                    <select id="np-visual-style" class="form-select">
                        ${VISUAL_STYLES.map(v => `<option value="${v.toLowerCase()}">${v}</option>`).join('')}
                    </select>
                </div>
            </div>

            <div class="form-row">
                <!-- Voice Preference -->
                <div class="form-group">
                    <label class="form-label" for="np-voice">Voice Preference</label>
                    <input type="text" id="np-voice" class="form-input" placeholder="e.g., Male, deep, authoritative" value="Male, professional">
                </div>
                <!-- Resolution -->
                <div class="form-group">
                    <label class="form-label" for="np-resolution">Resolution</label>
                    <select id="np-resolution" class="form-select">
                        <option value="1080x1920" selected>1080×1920 (Full HD Vertical)</option>
                        <option value="720x1280">720×1280 (HD Vertical)</option>
                        <option value="1920x1080">1920×1080 (Full HD Landscape)</option>
                    </select>
                </div>
                <!-- FPS -->
                <div class="form-group">
                    <label class="form-label" for="np-fps">Frame Rate</label>
                    <select id="np-fps" class="form-select">
                        <option value="30" selected>30 FPS</option>
                        <option value="24">24 FPS</option>
                        <option value="60">60 FPS</option>
                    </select>
                </div>
            </div>

            <div class="divider"></div>

            <div class="btn-group">
                <button type="submit" class="btn btn-primary btn-lg" id="np-submit">🚀 Create Project</button>
                <button type="button" class="btn btn-secondary" id="np-save-preset">💾 Save as Preset</button>
                <button type="button" class="btn btn-ghost" id="np-load-preset">📂 Load Preset</button>
            </div>
        </form>
    `;
}

export async function init() {
    const form = document.getElementById('new-project-form');
    const durationSlider = document.getElementById('np-duration');
    const durationLabel = document.getElementById('np-duration-label');

    // Duration slider live update
    durationSlider.addEventListener('input', () => {
        durationLabel.textContent = `${durationSlider.value}s`;
    });

    // Quick category select
    document.getElementById('category-select').addEventListener('click', (e) => {
        const btn = e.target.closest('.quick-select-btn');
        if (!btn) return;
        document.querySelectorAll('#category-select .quick-select-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const cat = CATEGORIES[btn.dataset.idx];
        if (cat.topic) {
            document.getElementById('np-topic').value = cat.topic;
        }
    });

    // Form submit
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitBtn = document.getElementById('np-submit');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner"></span> Creating...';

        const payload = {
            topic: document.getElementById('np-topic').value.trim(),
            niche: document.getElementById('np-niche').value,
            target_audience: document.getElementById('np-audience').value.trim(),
            language: document.getElementById('np-language').value,
            duration: parseInt(durationSlider.value),
            tone: document.getElementById('np-tone').value,
            style: document.getElementById('np-style').value,
            platform: document.getElementById('np-platform').value,
            visual_style: document.getElementById('np-visual-style').value,
            voice_preference: document.getElementById('np-voice').value.trim(),
            resolution: document.getElementById('np-resolution').value,
            fps: parseInt(document.getElementById('np-fps').value),
        };

        if (!payload.topic) {
            showToast('warning', 'Topic required', 'Please enter a topic for your video.');
            submitBtn.disabled = false;
            submitBtn.innerHTML = '🚀 Create Project';
            return;
        }

        try {
            const project = await api('/projects', { method: 'POST', body: payload });
            showToast('success', 'Project Created', `"${payload.topic}" is ready.`);
            state.set('currentProject', project.id || project.project_id);
            navigateTo('script-editor');
        } catch (err) {
            showToast('error', 'Create Failed', err.message);
            submitBtn.disabled = false;
            submitBtn.innerHTML = '🚀 Create Project';
        }
    });

    // Save/Load presets (localStorage)
    document.getElementById('np-save-preset').addEventListener('click', () => {
        const name = prompt('Preset name:');
        if (!name) return;
        const preset = {
            niche: document.getElementById('np-niche').value,
            platform: document.getElementById('np-platform').value,
            language: document.getElementById('np-language').value,
            duration: durationSlider.value,
            tone: document.getElementById('np-tone').value,
            style: document.getElementById('np-style').value,
            visual_style: document.getElementById('np-visual-style').value,
            voice: document.getElementById('np-voice').value,
            resolution: document.getElementById('np-resolution').value,
            fps: document.getElementById('np-fps').value,
            audience: document.getElementById('np-audience').value,
        };
        const presets = JSON.parse(localStorage.getItem('ss_presets') || '{}');
        presets[name] = preset;
        localStorage.setItem('ss_presets', JSON.stringify(presets));
        showToast('success', 'Preset Saved', `"${name}" saved to local storage.`);
    });

    document.getElementById('np-load-preset').addEventListener('click', () => {
        const presets = JSON.parse(localStorage.getItem('ss_presets') || '{}');
        const names = Object.keys(presets);
        if (names.length === 0) {
            showToast('info', 'No Presets', 'No saved presets found.');
            return;
        }
        const name = prompt(`Available presets:\n${names.join('\n')}\n\nEnter name to load:`);
        if (!name || !presets[name]) return;
        const p = presets[name];
        if (p.niche) document.getElementById('np-niche').value = p.niche;
        if (p.platform) document.getElementById('np-platform').value = p.platform;
        if (p.language) document.getElementById('np-language').value = p.language;
        if (p.duration) { durationSlider.value = p.duration; durationLabel.textContent = `${p.duration}s`; }
        if (p.tone) document.getElementById('np-tone').value = p.tone;
        if (p.style) document.getElementById('np-style').value = p.style;
        if (p.visual_style) document.getElementById('np-visual-style').value = p.visual_style;
        if (p.voice) document.getElementById('np-voice').value = p.voice;
        if (p.resolution) document.getElementById('np-resolution').value = p.resolution;
        if (p.fps) document.getElementById('np-fps').value = p.fps;
        if (p.audience) document.getElementById('np-audience').value = p.audience;
        showToast('success', 'Preset Loaded', `"${name}" applied.`);
    });
}
