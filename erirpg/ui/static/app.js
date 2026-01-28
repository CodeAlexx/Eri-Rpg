/* EriRPG Dashboard - Client JavaScript */

// State
let eventSource = null;
let currentTab = 'runs';
let currentProject = null;

// Settings (stored in localStorage)
const defaultSettings = {
    sseInterval: 1.0,
    pageSize: 50,
    graphDepth: 3
};

function loadSettings() {
    try {
        const saved = localStorage.getItem('erirpg-settings');
        return saved ? { ...defaultSettings, ...JSON.parse(saved) } : defaultSettings;
    } catch {
        return defaultSettings;
    }
}

function saveSettings(settings) {
    localStorage.setItem('erirpg-settings', JSON.stringify(settings));
}

const settings = loadSettings();

// SSE Connection
function connectSSE() {
    if (eventSource) {
        eventSource.close();
    }

    const url = `/api/stream?interval=${settings.sseInterval}`;
    eventSource = new EventSource(url);

    eventSource.addEventListener('status', (e) => {
        try {
            const status = JSON.parse(e.data);
            updateDashboard(status);
            updateConnectionStatus(true);
        } catch (err) {
            console.error('SSE parse error:', err);
        }
    });

    eventSource.onerror = () => {
        updateConnectionStatus(false);
        // Reconnect after 5 seconds
        setTimeout(connectSSE, 5000);
    };

    eventSource.onopen = () => {
        updateConnectionStatus(true);
    };
}

function updateConnectionStatus(connected) {
    const dot = document.querySelector('.connection-dot');
    const text = document.querySelector('.connection-text');
    if (dot) {
        dot.classList.toggle('disconnected', !connected);
    }
    if (text) {
        text.textContent = connected ? 'Live' : 'Reconnecting...';
    }
}

// Dashboard updates
function updateDashboard(status) {
    // Update active task section
    const activeSection = document.getElementById('active-task');
    if (activeSection && status.active) {
        activeSection.innerHTML = renderActiveTask(status.active);
        activeSection.classList.remove('hidden');
    } else if (activeSection) {
        activeSection.classList.add('hidden');
    }

    // Update project stats if on dashboard
    if (status.projects && document.querySelector('.project-list')) {
        updateProjectStats(status.projects);
    }
}

function renderActiveTask(active) {
    const historyHtml = active.history.slice(-10).map(h => {
        const time = formatTime(h.timestamp);
        const result = h.result || '';
        const resultClass = result === 'pass' ? 'pass' : result === 'failed' ? 'fail' : 'running';
        return `
            <div class="history-item">
                <span class="history-time">${time}</span>
                <span class="history-action">${h.action || ''}</span>
                <span class="history-target">${h.file || h.details || ''}</span>
                <span class="history-result ${resultClass}">${result || (h.action === 'verifying' ? '●' : '')}</span>
            </div>
        `;
    }).join('');

    return `
        <div class="card active-card">
            <div class="active-header">
                <span class="active-project">${active.project}</span>
                <span class="status status-active">${active.phase}</span>
            </div>
            <div class="active-task">"${active.task}"</div>
            <div class="active-meta">
                <div class="active-meta-item">
                    <span class="active-meta-label">Phase:</span>
                    <span>${active.phase}</span>
                </div>
                <div class="active-meta-item">
                    <span class="active-meta-label">Waiting on:</span>
                    <span>${active.waiting_on || 'none'}</span>
                </div>
            </div>
            ${active.history.length > 0 ? `
                <div class="history">
                    <div class="history-title">History</div>
                    <div class="history-list">${historyHtml}</div>
                </div>
            ` : ''}
        </div>
    `;
}

function updateProjectStats(projects) {
    projects.forEach(p => {
        const item = document.querySelector(`[data-project="${p.name}"]`);
        if (item) {
            const statsEl = item.querySelector('.project-stats');
            if (statsEl) {
                statsEl.innerHTML = `
                    <span class="project-stat"><span class="num">${p.modules}</span> mod</span>
                    <span class="project-stat"><span class="num">${p.learned}</span> learned</span>
                `;
            }
            const timeEl = item.querySelector('.project-time');
            if (timeEl) {
                timeEl.textContent = p.last_active || '';
            }
        }
    });
}

function formatTime(timestamp) {
    if (!timestamp) return '';
    try {
        const date = new Date(timestamp);
        return date.toLocaleTimeString('en-US', {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    } catch {
        return timestamp;
    }
}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Ignore if typing in input
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
        if (e.key === 'Escape') {
            e.target.blur();
        }
        return;
    }

    switch (e.key) {
        case 'r':
            refresh();
            break;
        case '/':
            e.preventDefault();
            const searchInput = document.getElementById('search-input');
            if (searchInput) searchInput.focus();
            break;
        case 'Escape':
            closeModals();
            break;
        case '1': case '2': case '3': case '4':
        case '5': case '6': case '7':
            switchTab(parseInt(e.key));
            break;
    }
});

// Tab switching
function switchTab(num) {
    const tabs = ['runs', 'learnings', 'roadmap', 'decisions', 'git', 'graph', 'drift'];
    const tabName = tabs[num - 1];
    if (tabName && currentProject) {
        setActiveTab(tabName);
        loadTabContent(tabName);
    }
}

function setActiveTab(tabName) {
    currentTab = tabName;

    // Update tab buttons
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });

    // Update URL without reload
    const url = new URL(window.location);
    url.searchParams.set('tab', tabName);
    history.replaceState(null, '', url);
}

async function loadTabContent(tabName) {
    if (!currentProject) return;

    const container = document.getElementById('tab-content');
    if (!container) return;

    container.innerHTML = '<div class="empty">Loading...</div>';

    try {
        switch (tabName) {
            case 'runs':
                await loadRuns(container);
                break;
            case 'learnings':
                await loadLearnings(container);
                break;
            case 'roadmap':
                await loadRoadmap(container);
                break;
            case 'decisions':
                await loadDecisions(container);
                break;
            case 'git':
                await loadGit(container);
                break;
            case 'graph':
                await loadGraph(container);
                break;
            case 'drift':
                await loadDrift(container);
                break;
        }
    } catch (err) {
        container.innerHTML = `<div class="empty">Error loading content: ${err.message}</div>`;
    }
}

// Tab content loaders
async function loadRuns(container) {
    const res = await fetch(`/api/project/${currentProject}/runs`);
    const data = await res.json();

    if (data.error) {
        container.innerHTML = `<div class="empty">${data.error}</div>`;
        return;
    }

    const state = data.state || {};
    const runs = data.runs || [];

    let html = '';

    // Active run from state
    if (state.phase && state.phase !== 'idle') {
        html += `
            <div class="section">
                <div class="section-title">Active</div>
                <div class="card active-card">
                    <div class="active-task">"${state.current_task || 'Unknown task'}"</div>
                    <div class="active-meta">
                        <div class="active-meta-item">
                            <span class="active-meta-label">Phase:</span>
                            <span>${state.phase}</span>
                        </div>
                        <div class="active-meta-item">
                            <span class="active-meta-label">Waiting on:</span>
                            <span>${state.waiting_on || 'none'}</span>
                        </div>
                    </div>
                    ${state.history ? renderHistory(state.history) : ''}
                </div>
            </div>
        `;
    }

    // Previous runs
    if (runs.length > 0) {
        html += `
            <div class="section">
                <div class="section-title">Previous Runs</div>
                <div class="run-list">
                    ${runs.map(r => renderRunItem(r)).join('')}
                </div>
            </div>
        `;
    } else if (!state.phase || state.phase === 'idle') {
        html = '<div class="empty"><div class="empty-icon">📋</div>No runs yet</div>';
    }

    container.innerHTML = html;
}

function renderRunItem(run) {
    const goal = run.spec?.goal || run.plan?.goal || 'Unknown';
    const status = run.completed_at ? 'success' : 'active';
    const icon = status === 'success' ? '✓' : '▶';
    const started = run.started_at ? formatRelativeTime(run.started_at) : '';

    return `
        <div class="run-item">
            <span class="run-icon ${status}">${icon}</span>
            <div class="run-info">
                <div class="run-title">${goal}</div>
                <div class="run-details">${started}</div>
            </div>
            <span class="status status-${status}">${status}</span>
        </div>
    `;
}

function renderHistory(history) {
    const items = history.slice(-10);
    if (items.length === 0) return '';

    return `
        <div class="history">
            <div class="history-title">History</div>
            <div class="history-list">
                ${items.map(h => `
                    <div class="history-item">
                        <span class="history-time">${formatTime(h.timestamp)}</span>
                        <span class="history-action">${h.action || ''}</span>
                        <span class="history-target">${h.file || h.details || ''}</span>
                        <span class="history-result ${h.result === 'pass' ? 'pass' : h.result === 'failed' ? 'fail' : ''}">${h.result || ''}</span>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

async function loadLearnings(container) {
    const search = document.getElementById('search-input')?.value || '';
    const res = await fetch(`/api/project/${currentProject}/learnings?search=${encodeURIComponent(search)}&limit=${settings.pageSize}`);
    const data = await res.json();

    if (data.error) {
        container.innerHTML = `<div class="empty">${data.error}</div>`;
        return;
    }

    const learnings = data.learnings || [];
    const total = data.total || 0;
    const staleCount = data.stale_count || 0;

    let html = `
        <div class="card-header">
            <span>Coverage: ${total} files ${staleCount > 0 ? `<span class="status status-warning">${staleCount} stale</span>` : ''}</span>
        </div>
        <div class="search">
            <span class="search-icon">🔍</span>
            <input type="text" id="search-input" placeholder="Search files..." value="${search}" onkeyup="debounceSearch()">
        </div>
    `;

    if (learnings.length > 0) {
        html += `<div class="learning-list">${learnings.map(renderLearningItem).join('')}</div>`;
    } else {
        html += '<div class="empty">No learnings found</div>';
    }

    if (data.pages > 1) {
        html += `
            <div class="pagination">
                <span class="pagination-info">Page ${data.page} of ${data.pages}</span>
            </div>
        `;
    }

    container.innerHTML = html;
}

function renderLearningItem(l) {
    const staleClass = l.stale ? 'stale' : '';
    const outlierClass = l.is_outlier ? 'outlier' : '';

    return `
        <div class="learning-item ${staleClass} ${outlierClass}">
            <div class="learning-header">
                <span class="learning-path">${l.path}</span>
                <div class="learning-meta">
                    <span>conf: ${l.confidence?.toFixed(2) || '1.00'}</span>
                    <span>v${l.version || 1}</span>
                    ${l.stale ? '<span class="status status-warning">stale</span>' : ''}
                </div>
            </div>
            <div class="learning-summary">${l.summary || l.purpose || ''}</div>
            ${l.drift_pattern ? `
                <div class="learning-tags">
                    <span class="drift-tag">🏷 ${l.drift_pattern} (${l.drift_confidence?.toFixed(2) || '?'})</span>
                </div>
            ` : ''}
        </div>
    `;
}

let searchTimeout;
function debounceSearch() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => loadLearnings(document.getElementById('tab-content')), 300);
}

async function loadRoadmap(container) {
    const res = await fetch(`/api/project/${currentProject}/roadmap`);
    const data = await res.json();

    if (data.content) {
        container.innerHTML = `
            <div class="roadmap-content">${escapeHtml(data.content)}</div>
            <div style="margin-top: 12px; font-size: 0.75rem; color: var(--text-dimmed);">
                Source: .planning/ROADMAP.md
            </div>
        `;
    } else {
        container.innerHTML = '<div class="empty"><div class="empty-icon">📝</div>No roadmap found<br><small>.planning/ROADMAP.md</small></div>';
    }
}

async function loadDecisions(container) {
    const res = await fetch(`/api/project/${currentProject}/decisions`);
    const data = await res.json();

    const decisions = data.decisions || [];

    if (decisions.length > 0) {
        container.innerHTML = `
            <div class="section-title">Decisions (${decisions.length})</div>
            <div class="decision-list">
                ${decisions.map(d => `
                    <div class="decision-item">
                        <div class="decision-header">
                            <span class="decision-id">${d.id || ''}</span>
                            <span class="decision-time">${d.timestamp ? formatRelativeTime(d.timestamp) : ''}</span>
                        </div>
                        <div class="decision-choice">${d.choice || ''}</div>
                        <div class="decision-rationale">Rationale: ${d.rationale || ''}</div>
                        <div class="decision-context">Context: ${d.context || ''}</div>
                    </div>
                `).join('')}
            </div>
        `;
    } else {
        container.innerHTML = '<div class="empty"><div class="empty-icon">🎯</div>No decisions recorded</div>';
    }
}

async function loadGit(container) {
    const res = await fetch(`/api/project/${currentProject}/git`);
    const data = await res.json();

    const commits = data.commits || [];

    if (commits.length > 0) {
        container.innerHTML = `
            <div class="section-title">Git History</div>
            <div class="commit-list">
                ${commits.map(c => `
                    <div class="commit-item">
                        <span class="commit-dot ${c.is_erirpg ? 'erirpg' : ''}"></span>
                        <div class="commit-info">
                            <span class="commit-hash">${c.short_hash}</span>
                            <div class="commit-message">${escapeHtml(c.message)}</div>
                        </div>
                        <span class="commit-time">${c.time}</span>
                    </div>
                `).join('')}
            </div>
            <div style="margin-top: 16px; font-size: 0.75rem; color: var(--text-dimmed);">
                <span class="commit-dot erirpg" style="display: inline-block; width: 8px; height: 8px;"></span> = EriRPG commit
            </div>
        `;
    } else {
        container.innerHTML = '<div class="empty"><div class="empty-icon">📜</div>No git history</div>';
    }
}

async function loadGraph(container) {
    const res = await fetch(`/api/project/${currentProject}/graph`);
    const data = await res.json();

    const nodes = data.nodes || [];
    const edges = data.edges || [];
    const nodeCount = Array.isArray(nodes) ? nodes.length : Object.keys(nodes).length;
    const edgeCount = Array.isArray(edges) ? edges.length : Object.keys(edges).length;

    container.innerHTML = `
        <div class="graph-stats">
            <span class="graph-stat">Nodes: <span class="num">${nodeCount}</span></span>
            <span class="graph-stat">Edges: <span class="num">${edgeCount}</span></span>
        </div>
        <div id="graph-container">
            Graph visualization coming in v0.1.0
        </div>
    `;
}

async function loadDrift(container) {
    const res = await fetch(`/api/project/${currentProject}/drift`);
    const data = await res.json();

    const available = data.available;
    const patterns = data.patterns || [];
    const outliers = data.outliers || [];
    const enriched = data.enriched_count || 0;
    const total = data.total_learnings || 0;

    let html = `
        <div class="drift-status">
            ${available
                ? '<span class="drift-available">✓ Drift Available</span>'
                : '<span class="drift-unavailable">○ Drift Not Configured</span>'
            }
        </div>
    `;

    if (available) {
        html += `
            <div class="card-header">
                <span>Enriched: ${enriched}/${total} learnings (${total > 0 ? Math.round(enriched/total*100) : 0}%)</span>
            </div>
        `;

        if (patterns.length > 0) {
            html += `
                <div class="section">
                    <div class="section-title">Patterns (${patterns.length})</div>
                    <div class="pattern-list">
                        ${patterns.map(p => `
                            <div class="pattern-item">
                                <span class="pattern-name">${p.name || p.id}</span>
                                <span class="pattern-category">${p.category || ''}</span>
                                <span class="pattern-confidence">${(p.confidence || 0).toFixed(2)}</span>
                                <span class="pattern-status ${p._status || ''}">${p._status || ''}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        if (outliers.length > 0) {
            html += `
                <div class="outlier-list">
                    <div class="section-title">Outliers (${outliers.length})</div>
                    ${outliers.map(o => `
                        <div class="outlier-item">⚠ ${o}</div>
                    `).join('')}
                </div>
            `;
        }
    } else {
        html += '<div class="empty">Configure .drift/ directory to enable Drift analysis</div>';
    }

    container.innerHTML = html;
}

// Utilities
function formatRelativeTime(timestamp) {
    if (!timestamp) return '';
    try {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = (now - date) / 1000;

        if (diff < 60) return 'now';
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        return `${Math.floor(diff / 86400)}d ago`;
    } catch {
        return timestamp;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function refresh() {
    if (currentProject && currentTab) {
        loadTabContent(currentTab);
    } else {
        location.reload();
    }
}

function closeModals() {
    document.querySelectorAll('.modal-overlay').forEach(m => m.remove());
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Get current project from page
    const projectEl = document.querySelector('[data-current-project]');
    if (projectEl) {
        currentProject = projectEl.dataset.currentProject;
    }

    // Get current tab from URL
    const params = new URLSearchParams(window.location.search);
    const tab = params.get('tab');
    if (tab) {
        currentTab = tab;
        setActiveTab(tab);
    }

    // Connect SSE
    connectSSE();

    // Load initial tab content if on project page
    if (currentProject) {
        loadTabContent(currentTab);
    }

    // Tab click handlers
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            setActiveTab(tab.dataset.tab);
            loadTabContent(tab.dataset.tab);
        });
    });
});
