// EriRPG Dashboard - IDE Layout
// SSE, tree navigation, keyboard shortcuts

(function() {
  'use strict';

  // ─────────────────────────────────────────────────────────────
  // STATE
  // ─────────────────────────────────────────────────────────────

  const state = {
    selectedProject: null,
    selectedTab: null,
    projects: window.INITIAL_PROJECTS || [],
    active: window.INITIAL_ACTIVE || null,
    focusedIndex: -1,
    navigationItems: []
  };

  let eventSource = null;

  // ─────────────────────────────────────────────────────────────
  // SSE CONNECTION
  // ─────────────────────────────────────────────────────────────

  function connectSSE() {
    if (eventSource) {
      eventSource.close();
    }

    eventSource = new EventSource('/api/stream');
    const indicator = document.getElementById('live-indicator');

    eventSource.addEventListener('status', (e) => {
      try {
        const data = JSON.parse(e.data);
        state.active = data.active;
        updateActivityPanel(data.active);
      } catch (err) {
        console.error('SSE parse error:', err);
      }
    });

    eventSource.addEventListener('open', () => {
      indicator.classList.remove('disconnected');
    });

    eventSource.onerror = () => {
      indicator.classList.add('disconnected');
      eventSource.close();
      // Reconnect after 5s
      setTimeout(connectSSE, 5000);
    };
  }

  // ─────────────────────────────────────────────────────────────
  // ACTIVITY PANEL
  // ─────────────────────────────────────────────────────────────

  function updateActivityPanel(active) {
    const header = document.getElementById('task-header');
    const log = document.getElementById('activity-log');

    if (!active) {
      header.innerHTML = '<div class="no-task">No active task</div>';
      log.innerHTML = '<div class="no-activity">No activity yet</div>';
      return;
    }

    // Update header
    header.innerHTML = `
      <div class="task-name">${escapeHtml(active.task || 'Unknown task')}</div>
      <div class="task-meta">
        <span class="phase phase-${active.phase || 'idle'}">${active.phase || 'idle'}</span>
        <span class="waiting">waiting: ${active.waiting_on || 'none'}</span>
      </div>
    `;

    // Update log
    if (active.history && active.history.length > 0) {
      log.innerHTML = active.history.map(entry => `
        <div class="log-entry ${entry.result === 'running' ? 'active' : ''}">
          <span class="time">${escapeHtml(entry.timestamp || '')}</span>
          <span class="action action-${entry.action || ''}">${escapeHtml(entry.action || '')}</span>
          <span class="target">${escapeHtml(entry.target || '')}</span>
          <span class="result result-${entry.result || ''}">${formatResult(entry.result)}</span>
        </div>
      `).join('');

      // Auto-scroll to bottom
      log.scrollTop = log.scrollHeight;
    } else {
      log.innerHTML = '<div class="no-activity">No activity yet</div>';
    }
  }

  function formatResult(result) {
    switch (result) {
      case 'pass': return '&#10003;';
      case 'fail': return '&#10007;';
      case 'running': return '&#9679;';
      default: return escapeHtml(result || '');
    }
  }

  // ─────────────────────────────────────────────────────────────
  // TREE NAVIGATION
  // ─────────────────────────────────────────────────────────────

  window.toggleProject = function(projectName) {
    const projectEl = document.querySelector(`.project[data-project="${projectName}"]`);
    if (!projectEl) return;

    const isExpanded = projectEl.classList.contains('expanded');
    const tabsEl = projectEl.querySelector('.tabs');

    if (isExpanded) {
      projectEl.classList.remove('expanded');
      projectEl.classList.add('collapsed');
      tabsEl.classList.add('hidden');
    } else {
      projectEl.classList.remove('collapsed');
      projectEl.classList.add('expanded');
      tabsEl.classList.remove('hidden');
    }

    buildNavigationItems();
  };

  window.selectTab = function(projectName, tabName) {
    state.selectedProject = projectName;
    state.selectedTab = tabName;

    // Update sidebar highlighting
    document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
    const tabEl = document.querySelector(`[data-project="${projectName}"][data-tab="${tabName}"]`);
    if (tabEl) {
      tabEl.classList.add('active');
    }

    // Update status bar
    updateStatusBar(projectName);

    // Load content
    loadContent(projectName, tabName);
  };

  function buildNavigationItems() {
    state.navigationItems = [];
    const projects = document.querySelectorAll('.project');

    projects.forEach(project => {
      state.navigationItems.push({
        type: 'project',
        name: project.dataset.project,
        element: project.querySelector('.project-header')
      });

      if (project.classList.contains('expanded')) {
        const tabs = project.querySelectorAll('.tab');
        tabs.forEach(tab => {
          state.navigationItems.push({
            type: 'tab',
            project: tab.dataset.project,
            tab: tab.dataset.tab,
            element: tab
          });
        });
      }
    });
  }

  function updateFocus(index) {
    // Remove old focus
    state.navigationItems.forEach(item => {
      item.element.classList.remove('focused');
    });

    state.focusedIndex = index;

    if (index >= 0 && index < state.navigationItems.length) {
      state.navigationItems[index].element.classList.add('focused');
      state.navigationItems[index].element.scrollIntoView({ block: 'nearest' });
    }
  }

  // ─────────────────────────────────────────────────────────────
  // CONTENT LOADING
  // ─────────────────────────────────────────────────────────────

  async function loadContent(project, tab) {
    const main = document.getElementById('main-content');
    main.innerHTML = '<div class="loading">Loading...</div>';

    try {
      const response = await fetch(`/content/${encodeURIComponent(project)}/${encodeURIComponent(tab)}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      main.innerHTML = await response.text();
    } catch (err) {
      main.innerHTML = `<div class="error">Failed to load: ${escapeHtml(err.message)}</div>`;
    }
  }

  // ─────────────────────────────────────────────────────────────
  // STATUS BAR
  // ─────────────────────────────────────────────────────────────

  function updateStatusBar(projectName) {
    const project = state.projects.find(p => p.name === projectName);
    if (!project) return;

    document.getElementById('status-project').textContent = project.name;
    document.getElementById('status-modules').textContent = `${project.modules || 0} modules`;

    const learned = project.learned || 0;
    const modules = project.modules || 0;
    const pct = modules > 0 ? Math.round((learned / modules) * 100) : 0;
    document.getElementById('status-learned').textContent = `${learned} learned (${pct}%)`;

    const staleEl = document.getElementById('status-stale');
    staleEl.textContent = `${project.stale || 0} stale`;
    staleEl.classList.toggle('warning', (project.stale || 0) > 0);
  }

  // ─────────────────────────────────────────────────────────────
  // KEYBOARD NAVIGATION
  // ─────────────────────────────────────────────────────────────

  function handleKeydown(e) {
    // Ignore if typing in input
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
      return;
    }

    switch (e.key) {
      case 'ArrowUp':
        e.preventDefault();
        navigateTree(-1);
        break;
      case 'ArrowDown':
        e.preventDefault();
        navigateTree(1);
        break;
      case 'ArrowLeft':
        e.preventDefault();
        collapseOrMove();
        break;
      case 'ArrowRight':
        e.preventDefault();
        expandOrMove();
        break;
      case 'Enter':
        e.preventDefault();
        selectFocused();
        break;
      case 'r':
        if (!e.ctrlKey && !e.metaKey) {
          e.preventDefault();
          refresh();
        }
        break;
    }
  }

  function navigateTree(direction) {
    if (state.navigationItems.length === 0) {
      buildNavigationItems();
    }

    let newIndex = state.focusedIndex + direction;
    if (newIndex < 0) newIndex = 0;
    if (newIndex >= state.navigationItems.length) newIndex = state.navigationItems.length - 1;

    updateFocus(newIndex);
  }

  function collapseOrMove() {
    if (state.focusedIndex < 0) return;

    const item = state.navigationItems[state.focusedIndex];
    if (!item) return;

    if (item.type === 'project') {
      const projectEl = document.querySelector(`.project[data-project="${item.name}"]`);
      if (projectEl && projectEl.classList.contains('expanded')) {
        toggleProject(item.name);
      }
    } else if (item.type === 'tab') {
      // Move to parent project
      const projectIndex = state.navigationItems.findIndex(
        i => i.type === 'project' && i.name === item.project
      );
      if (projectIndex >= 0) {
        updateFocus(projectIndex);
      }
    }
  }

  function expandOrMove() {
    if (state.focusedIndex < 0) return;

    const item = state.navigationItems[state.focusedIndex];
    if (!item) return;

    if (item.type === 'project') {
      const projectEl = document.querySelector(`.project[data-project="${item.name}"]`);
      if (projectEl && projectEl.classList.contains('collapsed')) {
        toggleProject(item.name);
        // Move to first tab
        buildNavigationItems();
        const firstTabIndex = state.navigationItems.findIndex(
          i => i.type === 'tab' && i.project === item.name
        );
        if (firstTabIndex >= 0) {
          updateFocus(firstTabIndex);
        }
      }
    }
  }

  function selectFocused() {
    if (state.focusedIndex < 0) return;

    const item = state.navigationItems[state.focusedIndex];
    if (!item) return;

    if (item.type === 'project') {
      toggleProject(item.name);
    } else if (item.type === 'tab') {
      selectTab(item.project, item.tab);
    }
  }

  function refresh() {
    if (state.selectedProject && state.selectedTab) {
      loadContent(state.selectedProject, state.selectedTab);
    }
  }

  // ─────────────────────────────────────────────────────────────
  // UTILITIES
  // ─────────────────────────────────────────────────────────────

  function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // ─────────────────────────────────────────────────────────────
  // INITIALIZATION
  // ─────────────────────────────────────────────────────────────

  function init() {
    connectSSE();
    buildNavigationItems();
    document.addEventListener('keydown', handleKeydown);

    // If there's an active project, expand it
    if (state.active && state.active.project) {
      const projectName = state.active.project;
      toggleProject(projectName);
      selectTab(projectName, 'runs');
    }
  }

  // Start when DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
