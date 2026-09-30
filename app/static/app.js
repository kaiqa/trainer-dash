/**
 * Training Planner Dashboard - Frontend Application
 * Modern vanilla JS dashboard for managing training sessions
 */

// ============================================
// Configuration & State
// ============================================
const API_BASE = '/api';
const WS_URL = `ws://${window.location.host}/ws`;

let state = {
    trainings: [],
    total: 0,
    page: 1,
    pageSize: 20,
    totalPages: 1,
    search: '',
    statusFilter: '',
    bodyTypeFilter: '',
    userNameFilter: '',
    dateFromFilter: '',
    dateToFilter: '',
    sortBy: 'created_at:desc',
    currentTraining: null,
    ws: null,
    wsReconnectAttempts: 0,
    maxReconnectAttempts: 10,
    reconnectDelay: 1000,
    settings: {
        host: '0.0.0.0',
        port: 5687,
        path: '/webhook/record-training'
    },
    theme: 'light' // 'light' or 'dark'
};

// ============================================
// DOM Elements
// ============================================
const elements = {
    // Navigation
    sidebar: document.getElementById('sidebar'),
    sidebarToggle: document.getElementById('sidebar-toggle'),
    sidebarCollapseToggle: document.getElementById('sidebar-collapse-toggle'),
    navItems: document.querySelectorAll('.nav-item'),
    pages: document.querySelectorAll('.page'),

    // Theme Toggle
    themeToggle: document.getElementById('theme-toggle'),
    themeToggleSun: document.querySelector('#theme-toggle .icon-sun'),
    themeToggleMoon: document.querySelector('#theme-toggle .icon-moon'),

    // Dashboard
    searchFilter: document.getElementById('searchFilter'),
    userNameFilter: document.getElementById('userNameFilter'),
    statusFilter: document.getElementById('statusFilter'),
    bodyTypeFilter: document.getElementById('bodyTypeFilter'),
    dateFromFilter: document.getElementById('dateFromFilter'),
    dateToFilter: document.getElementById('dateToFilter'),
    sortSelect: document.getElementById('sortSelect'),
    pageSizeSelect: document.getElementById('pageSizeSelect'),
    clearFiltersBtn: document.getElementById('clearFiltersBtn'),
    trainingsTbody: document.getElementById('trainings-tbody'),
    emptyState: document.getElementById('empty-state'),
    tableContainer: document.querySelector('.table-container'),
    prevPage: document.getElementById('prev-page'),
    nextPage: document.getElementById('next-page'),
    paginationInfo: document.getElementById('pagination-info'),
    refreshBtn: document.getElementById('refresh-btn'),
    refreshEmpty: document.getElementById('refresh-empty'),
    exportJson: document.getElementById('export-json'),
    exportCsv: document.getElementById('export-csv'),

    // Stats
    statTotal: document.getElementById('stat-total'),
    statPlanned: document.getElementById('stat-planned'),
    statDone: document.getElementById('stat-done'),
    statSkipped: document.getElementById('stat-skipped'),

    // Settings
    settingHost: document.getElementById('setting-host'),
    settingPort: document.getElementById('setting-port'),
    settingPath: document.getElementById('setting-training-path'),
    settingsWebhookUrl: document.getElementById('settings-training-webhook-url'),
    webhookUrlPreview: document.getElementById('training-webhook-url'),
    copyWebhookUrl: document.getElementById('copy-training-webhook-url'),
    copySettingsUrl: document.getElementById('copy-settings-training-url'),
    saveSettings: document.getElementById('save-settings'),
    resetSettings: document.getElementById('reset-settings'),
    appVersion: document.getElementById('app-version'),
    appEnv: document.getElementById('app-env'),
    appDb: document.getElementById('app-db'),

    // WebSocket Status
    wsStatus: document.getElementById('ws-status'),
    wsStatusText: document.getElementById('ws-status-text'),

    // Modals
    detailModal: document.getElementById('detail-modal'),
    modalTitle: document.getElementById('modal-title'),
    modalBody: document.getElementById('modal-body'),
    modalClose: document.getElementById('modal-close'),
    modalCloseBtn: document.getElementById('modal-close-btn'),
    modalDownload: document.getElementById('modal-download'),

    confirmModal: document.getElementById('confirm-modal'),
    confirmTitle: document.getElementById('confirm-title'),
    confirmBody: document.getElementById('confirm-body'),
    confirmCancel: document.getElementById('confirm-cancel'),
    confirmOk: document.getElementById('confirm-ok'),

    // Toast
    toastContainer: document.getElementById('toast-container'),
};

// ============================================
// Utility Functions
// ============================================
function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

function formatDateShort(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
    });
}

function formatDuration(minutes) {
    if (!minutes && minutes !== 0) return '-';
    if (minutes < 60) {
        return `${minutes} min`;
    }
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (mins === 0) {
        return `${hours}h`;
    }
    return `${hours}h ${mins}min`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ============================================
// Theme Functions
// ============================================
function initTheme() {
    // Check for saved theme preference or system preference
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    if (savedTheme) {
        state.theme = savedTheme;
    } else if (prefersDark) {
        state.theme = 'dark';
    }

    applyTheme(state.theme);
}

function applyTheme(theme) {
    state.theme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    updateThemeIcons();
}

function toggleTheme() {
    const newTheme = state.theme === 'light' ? 'dark' : 'light';
    applyTheme(newTheme);
}

function updateThemeIcons() {
    if (elements.themeToggleSun && elements.themeToggleMoon) {
        if (state.theme === 'dark') {
            elements.themeToggleSun.style.display = 'none';
            elements.themeToggleMoon.style.display = 'block';
        } else {
            elements.themeToggleSun.style.display = 'block';
            elements.themeToggleMoon.style.display = 'none';
        }
    }
}

// ============================================
// API Functions
// ============================================
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const config = {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
        ...options,
    };

    if (config.body && typeof config.body === 'object') {
        config.body = JSON.stringify(config.body);
    }

    const response = await fetch(url, config);

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }

    if (response.status === 204) {
        return null;
    }

    return response.json();
}

async function fetchTrainings() {
    const params = new URLSearchParams({
        page: state.page,
        page_size: state.pageSize,
    });

    if (state.search) params.append('search', state.search);
    if (state.userNameFilter) params.append('user_name', state.userNameFilter);
    if (state.statusFilter !== '') params.append('status', state.statusFilter);
    if (state.bodyTypeFilter !== '') params.append('body_type', state.bodyTypeFilter);
    if (state.dateFromFilter) params.append('date_from', state.dateFromFilter);
    if (state.dateToFilter) params.append('date_to', state.dateToFilter);
    params.append('sort', state.sortBy);

    const data = await apiRequest(`/trainings?${params.toString()}`);
    state.trainings = data.items;
    state.total = data.total;
    state.page = data.page;
    state.pageSize = data.page_size;
    state.totalPages = data.total_pages;

    updateStats();
    renderTrainingsTable();
    updatePagination();
}

async function fetchTraining(id) {
    return apiRequest(`/trainings/${id}`);
}

async function updateTraining(id, data) {
    return apiRequest(`/trainings/${id}`, {
        method: 'PATCH',
        body: data,
    });
}

async function deleteTraining(id) {
    return apiRequest(`/trainings/${id}`, { method: 'DELETE' });
}

async function exportTrainingsJson() {
    return apiRequest('/trainings/export/all');
}

async function exportTrainingsCsv() {
    const response = await fetch(`${API_BASE}/trainings/export/csv`);
    if (!response.ok) throw new Error('Export failed');
    return response.blob();
}

async function fetchSettings() {
    return apiRequest('/settings');
}

async function fetchWebhookUrl() {
    return apiRequest('/settings/webhook-url');
}

async function updateSetting(key, value, description) {
    return apiRequest(`/settings/${key}`, {
        method: 'PUT',
        body: { value, description },
    });
}

async function initializeDefaultSettings() {
    return apiRequest('/settings/initialize-defaults', { method: 'POST' });
}

// ============================================
// WebSocket Functions
// ============================================
function connectWebSocket() {
    if (state.ws && (state.ws.readyState === WebSocket.OPEN || state.ws.readyState === WebSocket.CONNECTING)) {
        return;
    }

    updateWsStatus('connecting');

    try {
        state.ws = new WebSocket(WS_URL);

        state.ws.onopen = () => {
            console.log('WebSocket connected');
            state.wsReconnectAttempts = 0;
            updateWsStatus('connected');
        };

        state.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                handleWebSocketMessage(message);
            } catch (e) {
                console.error('Failed to parse WS message:', e);
            }
        };

        state.ws.onclose = () => {
            console.log('WebSocket disconnected');
            updateWsStatus('disconnected');
            scheduleReconnect();
        };

        state.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            updateWsStatus('error');
        };
    } catch (e) {
        console.error('Failed to create WebSocket:', e);
        updateWsStatus('error');
        scheduleReconnect();
    }
}

function scheduleReconnect() {
    if (state.wsReconnectAttempts >= state.maxReconnectAttempts) {
        console.log('Max reconnect attempts reached');
        updateWsStatus('disconnected');
        return;
    }

    const delay = state.reconnectDelay * Math.pow(2, state.wsReconnectAttempts);
    state.wsReconnectAttempts++;

    console.log(`Reconnecting in ${delay}ms (attempt ${state.wsReconnectAttempts})`);
    setTimeout(connectWebSocket, delay);
}

function updateWsStatus(status) {
    const indicator = elements.wsStatus;
    const text = elements.wsStatusText;

    indicator.className = 'status-indicator';
    switch (status) {
        case 'connected':
            indicator.classList.add('connected');
            text.textContent = 'Connected';
            break;
        case 'connecting':
            indicator.classList.add('connecting');
            text.textContent = 'Connecting...';
            break;
        case 'disconnected':
            text.textContent = 'Disconnected';
            break;
        case 'error':
            text.textContent = 'Error';
            break;
    }
}

function handleWebSocketMessage(message) {
    switch (message.type) {
        case 'training_created':
            showToast('New training request received!', 'success');
            fetchTrainings();
            break;
        case 'training_updated':
            fetchTrainings();
            break;
        case 'training_deleted':
            fetchTrainings();
            break;
        case 'pong':
            // Heartbeat response
            break;
    }
}

function sendWsMessage(message) {
    if (state.ws && state.ws.readyState === WebSocket.OPEN) {
        state.ws.send(JSON.stringify(message));
    }
}

// ============================================
// Render Functions
// ============================================
function updateStats() {
    const planned = state.trainings.filter(m => m.status === 'planned').length;
    const done = state.trainings.filter(m => m.status === 'done').length;
    const skipped = state.trainings.filter(m => m.status === 'skipped').length;
    const today = state.trainings.filter(m => {
        const trainingDate = new Date(m.training_date).toDateString();
        const todayDate = new Date().toDateString();
        return trainingDate === todayDate;
    }).length;

    elements.statTotal.textContent = state.total;
    elements.statPlanned.textContent = planned;
    elements.statDone.textContent = done;
    elements.statSkipped.textContent = skipped;
}

function renderTrainingsTable() {
    const tbody = elements.trainingsTbody;
    const emptyState = elements.emptyState;

    if (state.trainings.length === 0) {
        tbody.innerHTML = '';
        emptyState.style.display = 'flex';
        elements.tableContainer.style.display = 'none';
        return;
    }

    emptyState.style.display = 'none';
    elements.tableContainer.style.display = 'block';

    tbody.innerHTML = state.trainings.map(training => `
        <tr data-id="${training.id}">
            <td class="cell-name">${escapeHtml(training.user_name)}</td>
            <td class="cell-type">${escapeHtml(training.type)}</td>
            <td class="cell-sets">${training.sets}</td>
            <td class="cell-reps">${training.repetitions}</td>
            <td class="cell-body">${escapeHtml(training.body_type || '-')}</td>
            <td class="cell-date">${formatDateShort(training.training_date)}</td>
            <td class="cell-time">${training.training_time ? training.training_time.substring(0,5) : '-'}</td>
            <td class="cell-duration">${training.time_spent_minutes ? training.time_spent_minutes + ' min' : '-'}</td>
            <td class="cell-weight">${training.weight ? training.weight + ' kg' : '-'}</td>
            <td class="cell-rating">${training.rating ? training.rating + '/10' : '-'}</td>
            <td class="cell-status">
                <span class="status-badge ${training.status}" data-status-toggle data-id="${training.id}" data-current-status="${training.status}" title="Click to cycle status (Planned → Done → Skipped → Planned)" style="cursor: pointer;">
                    ${training.status ? training.status.charAt(0).toUpperCase() + training.status.slice(1) : '-'}
                </span>
            </td>
            <td class="cell-actions">
                <div class="action-buttons">
                    <button class="action-btn view" data-action="view" data-id="${training.id}" title="View Details">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                            <circle cx="12" cy="12" r="3"/>
                        </svg>
                    </button>
                    <button class="action-btn status" data-action="status" data-id="${training.id}" title="Update Status">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                            <polyline points="22 4 12 14.01 9 11.01"/>
                        </svg>
                    </button>
                    <button class="action-btn download" data-action="download" data-id="${training.id}" title="Download JSON">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                            <polyline points="17 8 12 3 7 8"/>
                            <line x1="12" y1="3" x2="12" y2="15"/>
                        </svg>
                    </button>
                    <button class="action-btn delete" data-action="delete" data-id="${training.id}" title="Delete">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="3 6 5 6 21 6"/>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                        </svg>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');

    // Add click handlers for action buttons
    tbody.querySelectorAll('.action-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const action = btn.dataset.action;
            const id = parseInt(btn.dataset.id, 10);
            handleAction(action, id);
        });
    });

    // Status badge click - cycle through statuses
    tbody.querySelectorAll('[data-status-toggle]').forEach(badge => {
        badge.addEventListener('click', (e) => {
            e.stopPropagation();
            const id = parseInt(badge.dataset.id, 10);
            const currentStatus = badge.dataset.currentStatus;
            cycleTrainingStatus(id, currentStatus);
        });
    });

    // Row click for view details
    tbody.querySelectorAll('tr').forEach(row => {
        row.addEventListener('click', () => {
            const id = parseInt(row.dataset.id, 10);
            handleAction('view', id);
        });
    });
}

function updatePagination() {
    elements.paginationInfo.textContent = `Page ${state.page} of ${state.totalPages || 1}`;
    elements.prevPage.disabled = state.page <= 1;
    elements.nextPage.disabled = state.page >= state.totalPages;
}

function renderTrainingDetail(training) {
    state.currentTraining = training;
    elements.modalBody.innerHTML = `
        <div class="detail-grid">
            <div class="detail-label">ID</div>
            <div class="detail-value"><code>${training.id}</code></div>

            <div class="detail-label">Name</div>
            <div class="detail-value"><input type="text" id="edit-user-name" value="${escapeHtml(training.user_name)}" style="width:100%;padding:6px;border:1px solid var(--color-border);border-radius:var(--radius-sm);background:var(--color-bg-primary);color:var(--color-text-primary);font-size:0.875rem;" /></div>

            <div class="detail-label">Type</div>
            <div class="detail-value"><input type="text" id="edit-type" value="${escapeHtml(training.type)}" style="width:100%;padding:6px;border:1px solid var(--color-border);border-radius:var(--radius-sm);background:var(--color-bg-primary);color:var(--color-text-primary);font-size:0.875rem;" /></div>

            <div class="detail-label">Sets</div>
            <div class="detail-value"><input type="number" id="edit-sets" value="${training.sets}" style="width:100%;padding:6px;border:1px solid var(--color-border);border-radius:var(--radius-sm);background:var(--color-bg-primary);color:var(--color-text-primary);font-size:0.875rem;" /></div>

            <div class="detail-label">Repetitions</div>
            <div class="detail-value"><input type="number" id="edit-reps" value="${training.repetitions}" style="width:100%;padding:6px;border:1px solid var(--color-border);border-radius:var(--radius-sm);background:var(--color-bg-primary);color:var(--color-text-primary);font-size:0.875rem;" /></div>

            <div class="detail-label">Body Type</div>
            <div class="detail-value"><input type="text" id="edit-body-type" value="${escapeHtml(training.body_type)}" style="width:100%;padding:6px;border:1px solid var(--color-border);border-radius:var(--radius-sm);background:var(--color-bg-primary);color:var(--color-text-primary);font-size:0.875rem;" /></div>

            <div class="detail-label">Training Date</div>
            <div class="detail-value"><input type="date" id="edit-date" value="${training.training_date}" style="width:100%;padding:6px;border:1px solid var(--color-border);border-radius:var(--radius-sm);background:var(--color-bg-primary);color:var(--color-text-primary);font-size:0.875rem;" /></div>

            <div class="detail-label">Training Time</div>
            <div class="detail-value"><input type="time" id="edit-time" value="${training.training_time ? training.training_time.substring(0,5) : ''}" style="width:100%;padding:6px;border:1px solid var(--color-border);border-radius:var(--radius-sm);background:var(--color-bg-primary);color:var(--color-text-primary);font-size:0.875rem;" /></div>

            <div class="detail-label">Duration (min)</div>
            <div class="detail-value"><input type="number" id="edit-duration" value="${training.time_spent_minutes || ''}" style="width:100%;padding:6px;border:1px solid var(--color-border);border-radius:var(--radius-sm);background:var(--color-bg-primary);color:var(--color-text-primary);font-size:0.875rem;" /></div>

            <div class="detail-label">Weight (kg)</div>
            <div class="detail-value"><input type="number" id="edit-weight" value="${training.weight || ''}" step="0.1" style="width:100%;padding:6px;border:1px solid var(--color-border);border-radius:var(--radius-sm);background:var(--color-bg-primary);color:var(--color-text-primary);font-size:0.875rem;" /></div>

            <div class="detail-label">Rating (1-10)</div>
            <div class="detail-value"><input type="number" id="edit-rating" min="1" max="10" value="${training.rating || ''}" style="width:100%;padding:6px;border:1px solid var(--color-border);border-radius:var(--radius-sm);background:var(--color-bg-primary);color:var(--color-text-primary);font-size:0.875rem;" /></div>

            <div class="detail-label">Injuries</div>
            <div class="detail-value">
                <select id="edit-injuries" style="width:100%;padding:6px;border:1px solid var(--color-border);border-radius:var(--radius-sm);background:var(--color-bg-primary);color:var(--color-text-primary);font-size:0.875rem;">
                    <option value="no" ${training.injuries === 'no' ? 'selected' : ''}>No</option>
                    <option value="yes" ${training.injuries === 'yes' ? 'selected' : ''}>Yes</option>
                </select>
            </div>

            <div class="detail-label">Pain</div>
            <div class="detail-value">
                <select id="edit-pain" style="width:100%;padding:6px;border:1px solid var(--color-border);border-radius:var(--radius-sm);background:var(--color-bg-primary);color:var(--color-text-primary);font-size:0.875rem;">
                    <option value="no" ${training.pain === 'no' ? 'selected' : ''}>No</option>
                    <option value="yes" ${training.pain === 'yes' ? 'selected' : ''}>Yes</option>
                </select>
            </div>

            <div class="detail-label">Pain Source</div>
            <div class="detail-value"><input type="text" id="edit-pain-source" value="${training.pain_source || ''}" placeholder="e.g. knees" style="width:100%;padding:6px;border:1px solid var(--color-border);border-radius:var(--radius-sm);background:var(--color-bg-primary);color:var(--color-text-primary);font-size:0.875rem;" /></div>

            <div class="detail-label">Session Notes</div>
            <div class="detail-value"><textarea id="edit-notes" rows="3" style="width:100%;padding:8px;border:1px solid var(--color-border);border-radius:var(--radius-sm);background:var(--color-bg-primary);color:var(--color-text-primary);font-size:0.875rem;font-family:inherit;resize:vertical;">${escapeHtml(training.session_notes || '')}</textarea></div>

            <div class="detail-label">Status</div>
            <div class="detail-value">
                <select id="edit-status" style="width:100%;padding:6px;border:1px solid var(--color-border);border-radius:var(--radius-sm);background:var(--color-bg-primary);color:var(--color-text-primary);font-size:0.875rem;">
                    <option value="planned" ${training.status === 'planned' ? 'selected' : ''}>Planned</option>
                    <option value="done" ${training.status === 'done' ? 'selected' : ''}>Done</option>
                    <option value="skipped" ${training.status === 'skipped' ? 'selected' : ''}>Skipped</option>
                </select>
            </div>

            <div class="detail-label">Created At</div>
            <div class="detail-value">${formatDate(training.created_at)}</div>

            <div class="detail-label">Updated At</div>
            <div class="detail-value">${formatDate(training.updated_at)}</div>
        </div>
    `;
}

function updateSettingsForm(settings) {
    state.settings = { ...state.settings, ...settings };
    elements.settingHost.value = state.settings.host;
    elements.settingPort.value = state.settings.port;
    elements.settingPath.value = state.settings.path;
    updateWebhookUrlDisplay();
}

function updateWebhookUrlDisplay() {
    const host = state.settings.host === '0.0.0.0' ? 'localhost' : state.settings.host;
    const url = `http://${host}:${state.settings.port}${state.settings.path}`;
    elements.settingsWebhookUrl.textContent = url;
    elements.webhookUrlPreview.textContent = url;
}

async function loadSettings() {
    try {
        const settings = await fetchSettings();
        const settingsMap = {};
        settings.forEach(s => settingsMap[s.key] = s.value);
        updateSettingsForm({
            host: settingsMap.webhook_host || '0.0.0.0',
            port: parseInt(settingsMap.webhook_port || '5687', 10),
            path: settingsMap.webhook_path || '/webhook/req-meeting',
        });
    } catch (e) {
        console.error('Failed to load settings:', e);
    }
}

async function loadWebhookUrl() {
    try {
        const data = await fetchWebhookUrl();
        updateSettingsForm({
            host: data.host,
            port: data.port,
            path: data.path,
        });
    } catch (e) {
        console.error('Failed to load webhook URL:', e);
    }
}

// ============================================
// Action Handlers
// ============================================
let confirmCallback = null;

function handleAction(action, id) {
    const training = state.trainings.find(m => m.id === id);
    if (!training && action !== 'view') return;

    switch (action) {
        case 'view':
            if (training) {
                renderTrainingDetail(training);
                openModal(elements.detailModal);
            }
            break;

        case 'status':
            showStatusModal(training);
            break;

        case 'delete':
            showConfirm(
                'Delete Training Session',
                'Are you sure you want to permanently delete this training session? This action cannot be undone.',
                () => performDelete(training.id)
            );
            break;

        case 'download':
            downloadTrainingJson(training);
            break;
    }
}

// Status cycle: planned → done → skipped → planned
const STATUS_CYCLE = ['planned', 'done', 'skipped'];

async function cycleTrainingStatus(id, currentStatus) {
    const currentIndex = STATUS_CYCLE.indexOf(currentStatus);
    const nextIndex = (currentIndex + 1) % STATUS_CYCLE.length;
    const newStatus = STATUS_CYCLE[nextIndex];

    try {
        await apiRequest(`/trainings/${id}/status`, {
            method: 'PATCH',
            body: { status: newStatus }
        });
        showToast(`Status updated to ${newStatus}`, 'success');
        fetchTrainings();
    } catch (e) {
        showToast(`Failed to update status: ${e.message}`, 'error');
    }
}

async function performToggle(id, isActive) {
    try {
        await updateTraining(id, { is_active: isActive });
        showToast(`Training ${isActive ? 'activated' : 'deactivated'}`, 'success');
        fetchTrainings();
    } catch (e) {
        showToast(`Failed to update: ${e.message}`, 'error');
    }
}

async function performStatusUpdate(id, newStatus) {
    try {
        await apiRequest(`/trainings/${id}/status`, {
            method: 'PATCH',
            body: { status: newStatus }
        });
        showToast(`Status updated to ${newStatus}`, 'success');
        fetchTrainings();
    } catch (e) {
        showToast(`Failed to update status: ${e.message}`, 'error');
    }
}

function showStatusModal(training) {
    const statuses = ['planned', 'done', 'skipped'];
    const options = statuses.map(s =>
        `<option value="${s}" ${s === training.status ? 'selected' : ''}>${s.charAt(0).toUpperCase() + s.slice(1)}</option>`
    ).join('');

    const content = `
        <div class="detail-grid">
            <div class="detail-label">Current Status</div>
            <div class="detail-value">
                <span class="status-badge ${training.status}">
                    ${training.status ? training.status.charAt(0).toUpperCase() + training.status.slice(1) : '-'}
                </span>
            </div>
            <div class="detail-label">New Status</div>
            <div class="detail-value">
                <select id="status-select" class="form-select">
                    ${options}
                </select>
            </div>
        </div>
    `;

    elements.confirmTitle.textContent = 'Update Status';
    elements.confirmBody.innerHTML = content;

    confirmCallback = () => {
        const select = document.getElementById('status-select');
        const newStatus = select.value;
        if (newStatus !== training.status) {
            performStatusUpdate(training.id, newStatus);
        }
    };
    openModal(elements.confirmModal);
}

async function performDelete(id) {
    try {
        await deleteTraining(id);
        showToast('Training deleted', 'success');
        fetchTrainings();
    } catch (e) {
        showToast(`Failed to delete: ${e.message}`, 'error');
    }
}

function downloadTrainingJson(training) {
    const dataStr = JSON.stringify(training, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `training_${training.id}_${training.user_name.replace(/\s+/g, '_')}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('Training downloaded', 'success');
}

async function handleExportJson() {
    try {
        const data = await exportTrainingsJson();
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `trainings_export_${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);
        showToast('Export downloaded', 'success');
    } catch (e) {
        showToast(`Export failed: ${e.message}`, 'error');
    }
}

async function handleExportCsv() {
    try {
        const blob = await exportTrainingsCsv();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `trainings_export_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        showToast('CSV export downloaded', 'success');
    } catch (e) {
        showToast(`Export failed: ${e.message}`, 'error');
    }
}

async function handleSaveSettings() {
    try {
        await updateSetting('webhook_host', elements.settingHost.value, 'IP address to bind webhook server');
        await updateSetting('webhook_port', elements.settingPort.value, 'Port for webhook server');
        await updateSetting('webhook_path', elements.settingPath.value, 'Webhook endpoint path');
        showToast('Settings saved. Restart required for changes to take effect.', 'success');
        loadWebhookUrl();
    } catch (e) {
        showToast(`Failed to save: ${e.message}`, 'error');
    }
}

async function handleResetSettings() {
    try {
        await initializeDefaultSettings();
        showToast('Settings reset to defaults', 'success');
        loadSettings();
    } catch (e) {
        showToast(`Failed to reset: ${e.message}`, 'error');
    }
}

// ============================================
// Modal Functions
// ============================================
function openModal(modal) {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeModal(modal) {
    modal.classList.remove('active');
    document.body.style.overflow = '';
}

function showConfirm(title, message, onConfirm) {
    elements.confirmTitle.textContent = title;
    elements.confirmBody.textContent = message;
    confirmCallback = onConfirm;
    openModal(elements.confirmModal);
}

// ============================================
// Toast Notifications
// ============================================
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = {
        success: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
        error: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
        warning: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
        info: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
    };

    toast.innerHTML = `
        <div class="toast-icon">${icons[type]}</div>
        <div class="toast-message">${escapeHtml(message)}</div>
        <button class="toast-close" aria-label="Dismiss">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
        </button>
    `;

    toast.querySelector('.toast-close').addEventListener('click', () => {
        toast.remove();
    });

    elements.toastContainer.appendChild(toast);

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        if (toast.parentNode) {
            toast.style.animation = 'slideIn 0.2s ease reverse';
            setTimeout(() => toast.remove(), 200);
        }
    }, 5000);
}

// ============================================
// Event Listeners
// ============================================
function setupEventListeners() {
    // Sidebar toggle (mobile)
    elements.sidebarToggle.addEventListener('click', () => {
        elements.sidebar.classList.toggle('collapsed');
    });

    // Sidebar collapse/expand toggle (desktop)
    if (elements.sidebarCollapseToggle) {
        elements.sidebarCollapseToggle.addEventListener('click', () => {
            elements.sidebar.classList.toggle('collapsed');
        });
    }

    // Theme toggle
    if (elements.themeToggle) {
        elements.themeToggle.addEventListener('click', toggleTheme);
    }

    // Navigation
    elements.navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const page = item.dataset.page;
            switchPage(page);

            elements.navItems.forEach(n => n.classList.remove('active'));
            item.classList.add('active');

            // Close sidebar on mobile
            if (window.innerWidth < 1024) {
                elements.sidebar.classList.remove('open');
            }
        });
    });

    // Search with debounce
    const debouncedSearch = debounce(() => {
        state.search = elements.searchFilter.value.trim();
        state.page = 1;
        fetchTrainings();
    }, 300);

    elements.searchFilter.addEventListener('input', debouncedSearch);

    // User Name filter with debounce
    const debouncedUserName = debounce(() => {
        state.userNameFilter = elements.userNameFilter.value.trim();
        state.page = 1;
        fetchTrainings();
    }, 300);

    elements.userNameFilter.addEventListener('input', debouncedUserName);

    // Filters
    elements.statusFilter.addEventListener('change', () => {
        state.statusFilter = elements.statusFilter.value;
        state.page = 1;
        fetchTrainings();
    });

    elements.bodyTypeFilter.addEventListener('change', () => {
        state.bodyTypeFilter = elements.bodyTypeFilter.value;
        state.page = 1;
        fetchTrainings();
    });

    elements.dateFromFilter.addEventListener('change', () => {
        state.dateFromFilter = elements.dateFromFilter.value;
        state.page = 1;
        fetchTrainings();
    });

    elements.dateToFilter.addEventListener('change', () => {
        state.dateToFilter = elements.dateToFilter.value;
        state.page = 1;
        fetchTrainings();
    });

    // Clear filters
    elements.clearFiltersBtn.addEventListener('click', () => {
        elements.searchFilter.value = '';
        elements.userNameFilter.value = '';
        elements.statusFilter.value = '';
        elements.bodyTypeFilter.value = '';
        elements.dateFromFilter.value = '';
        elements.dateToFilter.value = '';
        state.search = '';
        state.userNameFilter = '';
        state.statusFilter = '';
        state.bodyTypeFilter = '';
        state.dateFromFilter = '';
        state.dateToFilter = '';
        state.page = 1;
        fetchTrainings();
    });

    elements.sortSelect.addEventListener('change', () => {
        state.sortBy = elements.sortSelect.value;
        state.page = 1;
        fetchTrainings();
    });

    elements.pageSizeSelect.addEventListener('change', () => {
        state.pageSize = parseInt(elements.pageSizeSelect.value, 10);
        state.page = 1;
        fetchTrainings();
    });

    // Pagination
    elements.prevPage.addEventListener('click', () => {
        if (state.page > 1) {
            state.page--;
            fetchTrainings();
        }
    });

    elements.nextPage.addEventListener('click', () => {
        if (state.page < state.totalPages) {
            state.page++;
            fetchTrainings();
        }
    });

    // Refresh
    elements.refreshBtn.addEventListener('click', fetchTrainings);
    elements.refreshEmpty.addEventListener('click', fetchTrainings);

    // Export
    elements.exportJson.addEventListener('click', handleExportJson);
    elements.exportCsv.addEventListener('click', handleExportCsv);

    // Settings
    elements.saveSettings.addEventListener('click', handleSaveSettings);
    elements.resetSettings.addEventListener('click', handleResetSettings);

    // Settings form live URL update
    [elements.settingHost, elements.settingPort, elements.settingPath].forEach(el => {
        el.addEventListener('input', updateWebhookUrlDisplay);
    });

    // Copy webhook URL
    elements.copyWebhookUrl.addEventListener('click', () => copyToClipboard(elements.webhookUrlPreview.textContent));
    elements.copySettingsUrl.addEventListener('click', () => copyToClipboard(elements.settingsWebhookUrl.textContent));

    // Modals
    elements.modalClose.addEventListener('click', () => closeModal(elements.detailModal));
    elements.modalCloseBtn.addEventListener('click', () => closeModal(elements.detailModal));
    elements.modalDownload.addEventListener('click', () => {
        if (state.currentTraining) {
            downloadTrainingJson(state.currentTraining);
        }
    });

    // Save Changes in detail modal
    document.getElementById('modal-save').addEventListener('click', async () => {
        if (!state.currentTraining) return;
        try {
            const id = state.currentTraining.id;
            const updateData = {
                user_name: document.getElementById('edit-user-name').value,
                type: document.getElementById('edit-type').value,
                body_type: document.getElementById('edit-body-type').value,
                sets: parseInt(document.getElementById('edit-sets').value, 10) || 0,
                repetitions: parseInt(document.getElementById('edit-reps').value, 10) || 0,
                training_date: document.getElementById('edit-date').value,
                training_time: document.getElementById('edit-time').value ? document.getElementById('edit-time').value + ':00' : null,
                time_spent_minutes: parseInt(document.getElementById('edit-duration').value, 10) || 0,
                weight: document.getElementById('edit-weight').value ? parseFloat(document.getElementById('edit-weight').value) : null,
                rating: document.getElementById('edit-rating').value ? parseInt(document.getElementById('edit-rating').value, 10) : null,
                injuries: document.getElementById('edit-injuries').value,
                pain: document.getElementById('edit-pain').value,
                pain_source: document.getElementById('edit-pain-source').value || null,
                session_notes: document.getElementById('edit-notes').value,
                status: document.getElementById('edit-status').value,
            };
            await apiRequest(`/trainings/${id}`, {
                method: 'PATCH',
                body: updateData,
            });
            showToast('Training updated successfully', 'success');
            fetchTrainings();
            closeModal(elements.detailModal);
        } catch (e) {
            showToast(`Failed to save: ${e.message}`, 'error');
        }
    });

    elements.confirmCancel.addEventListener('click', () => closeModal(elements.confirmModal));
    elements.confirmOk.addEventListener('click', () => {
        if (confirmCallback) {
            confirmCallback();
            confirmCallback = null;
        }
        closeModal(elements.confirmModal);
    });

    // Close modals on overlay click
    [elements.detailModal, elements.confirmModal].forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeModal(modal);
            }
        });
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeModal(elements.detailModal);
            closeModal(elements.confirmModal);
        }
        if (e.key === 'f' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            elements.searchInput.focus();
        }
    });

    // Table header sorting
    document.querySelectorAll('.trainings-table th[data-sort]').forEach(th => {
        th.addEventListener('click', () => {
            const sortKey = th.dataset.sort;
            const currentSort = state.sortBy;
            let newSort;

            if (currentSort.startsWith(sortKey + ':asc')) {
                newSort = `${sortKey}:desc`;
            } else {
                newSort = `${sortKey}:asc`;
            }

            state.sortBy = newSort;
            state.page = 1;
            fetchTrainings();

            // Update sort indicators
            document.querySelectorAll('.trainings-table th').forEach(h => {
                h.classList.remove('sorted-asc', 'sorted-desc');
            });
            th.classList.add(newSort.endsWith('asc') ? 'sorted-asc' : 'sorted-desc');
        });
    });
}

async function renderAnalytics() {
    try {
        // Fetch analytics data using the stats endpoint
        const stats = await apiRequest('/trainings/stats/summary');

        // Update stat cards
        document.getElementById('analytics-total').textContent = stats.total_sessions || state.trainings.length || 0;
        document.getElementById('analytics-planned').textContent = stats.status_counts?.planned || 0;
        document.getElementById('analytics-done').textContent = stats.status_counts?.done || 0;
        document.getElementById('analytics-skipped').textContent = stats.status_counts?.skipped || 0;

        // Render Status Doughnut Chart
        const ctxStatus = document.getElementById('chart-status').getContext('2d');
        if (window.statusChartInstance) {
            window.statusChartInstance.destroy();
        }
        const statusLabels = ['Planned', 'Done', 'Skipped'];
        const statusData = [
            stats.status_counts?.planned || 0,
            stats.status_counts?.done || 0,
            stats.status_counts?.skipped || 0,
        ];
        const statusColors = ['#3b82f6', '#10b981', '#ef4444'];
        window.statusChartInstance = new Chart(ctxStatus, {
            type: 'doughnut',
            data: {
                labels: statusLabels,
                datasets: [{
                    data: statusData,
                    backgroundColor: statusColors,
                    borderColor: '#fff',
                    borderWidth: 2,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { color: '#64748b', font: { family: "'Inter', sans-serif" } } },
                },
            },
        });

        // Render Body Type Bar Chart
        const bodyTypeCounts = stats.body_type_counts || {};
        const bodyLabels = Object.keys(bodyTypeCounts);
        const bodyData = Object.values(bodyTypeCounts);
        const ctxBody = document.getElementById('chart-body-type').getContext('2d');
        if (window.bodyTypeChartInstance) {
            window.bodyTypeChartInstance.destroy();
        }
        window.bodyTypeChartInstance = new Chart(ctxBody, {
            type: 'bar',
            data: {
                labels: bodyLabels,
                datasets: [{
                    label: 'Sessions',
                    data: bodyData,
                    backgroundColor: '#6366f1',
                    borderRadius: 6,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                },
                scales: {
                    y: { beginAtZero: true, ticks: { color: '#64748b' } },
                    x: { ticks: { color: '#64748b' } },
                },
            },
        });

        // Render Type Bar Chart
        const typeCounts = stats.type_counts || {};
        const typeLabels = Object.keys(typeCounts);
        const typeData = Object.values(typeCounts);
        const ctxType = document.getElementById('chart-type').getContext('2d');
        if (window.typeChartInstance) {
            window.typeChartInstance.destroy();
        }
        window.typeChartInstance = new Chart(ctxType, {
            type: 'bar',
            data: {
                labels: typeLabels,
                datasets: [{
                    label: 'Sessions',
                    data: typeData,
                    backgroundColor: '#10b981',
                    borderRadius: 6,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                },
                scales: {
                    y: { beginAtZero: true, ticks: { color: '#64748b' } },
                    x: { ticks: { color: '#64748b' } },
                },
            },
        });

        // Render Rating Doughnut Chart
        // We can aggregate ratings from state.trainings or use stats if available
        const ratings = state.trainings.map(t => t.rating).filter(r => r !== null && r !== undefined);
        const ratingBinned = { '1-3': 0, '4-6': 0, '7-8': 0, '9-10': 0 };
        ratings.forEach(r => {
            if (r <= 3) ratingBinned['1-3']++;
            else if (r <= 6) ratingBinned['4-6']++;
            else if (r <= 8) ratingBinned['7-8']++;
            else ratingBinned['9-10']++;
        });
        const ratingLabels = Object.keys(ratingBinned);
        const ratingDataset = Object.values(ratingBinned);
        const ctxRating = document.getElementById('chart-rating').getContext('2d');
        if (window.ratingChartInstance) {
            window.ratingChartInstance.destroy();
        }
        window.ratingChartInstance = new Chart(ctxRating, {
            type: 'doughnut',
            data: {
                labels: ratingLabels,
                datasets: [{
                    data: ratingDataset,
                    backgroundColor: ['#ef4444', '#f59e0b', '#6366f1', '#10b981'],
                    borderColor: '#fff',
                    borderWidth: 2,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { color: '#64748b', font: { family: "'Inter', sans-serif" } } },
                },
            },
        });

        // Render Leaderboard (per user max performance - grouped bar)
        const userPerf = {};
        state.trainings.forEach(t => {
            if (!userPerf[t.user_name]) {
                userPerf[t.user_name] = { max_duration: 0, max_weight: 0, max_reps: 0, max_sets: 0 };
            }
            userPerf[t.user_name].max_duration = Math.max(userPerf[t.user_name].max_duration, t.time_spent_minutes || 0);
            userPerf[t.user_name].max_weight = Math.max(userPerf[t.user_name].max_weight, t.weight || 0);
            userPerf[t.user_name].max_reps = Math.max(userPerf[t.user_name].max_reps, t.repetitions || 0);
            userPerf[t.user_name].max_sets = Math.max(userPerf[t.user_name].max_sets, t.sets || 0);
        });
        const topUsers = Object.entries(userPerf)
            .sort((a, b) => b[1].max_duration - a[1].max_duration)
            .slice(0, 6);
        const lbLabelsCorrect = topUsers.map(u => {
            const parts = u[0].split(' ');
            return parts[0] + ' ' + (parts.length > 1 ? parts.slice(-1)[0][0] + '.' : '');
        });
        const lbDurations = topUsers.map(u => u[1].max_duration);
        const lbWeights = topUsers.map(u => Math.round(u[1].max_weight));
        const lbReps = topUsers.map(u => u[1].max_reps);
        const lbSets = topUsers.map(u => u[1].max_sets);
        const ctxLeaderboard = document.getElementById('chart-leaderboard').getContext('2d');
        if (window.leaderboardChartInstance) {
            window.leaderboardChartInstance.destroy();
        }
        window.leaderboardChartInstance = new Chart(ctxLeaderboard, {
            type: 'bar',
            data: {
                labels: lbLabelsCorrect,
                datasets: [
                    {
                        label: 'Max Duration (min)',
                        data: lbDurations,
                        backgroundColor: '#6366f1',
                        borderRadius: 4,
                        yAxisID: 'y',
                    },
                    {
                        label: 'Max Weight (kg)',
                        data: lbWeights,
                        backgroundColor: '#10b981',
                        borderRadius: 4,
                        yAxisID: 'y1',
                    },
                    {
                        label: 'Max Reps',
                        data: lbReps,
                        backgroundColor: '#f59e0b',
                        borderRadius: 4,
                        yAxisID: 'y',
                    },
                    {
                        label: 'Max Sets',
                        data: lbSets,
                        backgroundColor: '#ef4444',
                        borderRadius: 4,
                        yAxisID: 'y',
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top', labels: { color: '#64748b' } },
                    title: { display: true, text: 'Top Users — Max Performance Metrics', color: '#1e293b', font: { size: 16, weight: '600' } },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: 'Duration / Sets / Reps', color: '#64748b' },
                        ticks: { color: '#64748b' },
                        grid: { color: '#e2e8f0' },
                    },
                    y1: {
                        beginAtZero: true,
                        position: 'right',
                        title: { display: true, text: 'Weight (kg)', color: '#64748b' },
                        ticks: { color: '#64748b' },
                        grid: { drawOnChartArea: false },
                    },
                    x: {
                        ticks: { color: '#64748b', maxRotation: 45 },
                        grid: { display: false },
                    },
                },
            },
        });
    } catch (e) {
        console.error('Failed to render analytics:', e);
        showToast('Failed to load analytics', 'error');
    }
}

function switchPage(pageName) {
    elements.pages.forEach(page => {
        page.classList.toggle('active', page.id === `page-${pageName}`);
    });

    // Sync nav highlight
    elements.navItems.forEach(n => n.classList.remove('active'));
    const activeNav = document.querySelector(`.nav-item[data-page="${pageName}"]`);
    if (activeNav) activeNav.classList.add('active');

    const titles = {
        dashboard: 'Dashboard',
        analytics: 'Analytics',
        settings: 'Settings',
    };
    elements.pageTitle.textContent = titles[pageName] || 'Dashboard';

    // Load page-specific data
    if (pageName === 'settings') {
        loadSettings();
    } else if (pageName === 'dashboard') {
        fetchTrainings();
    } else if (pageName === 'analytics') {
        renderAnalytics();
    }
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Copied to clipboard', 'success');
    }).catch(() => {
        showToast('Failed to copy', 'error');
    });
}

// ============================================
// Initialization
// ============================================
async function init() {
    console.log('Initializing Training Request Dashboard...');

    // Initialize theme before setting up event listeners
    initTheme();
    setupEventListeners();
    connectWebSocket();

    // Load initial data
    await Promise.all([
        fetchTrainings(),
        loadWebhookUrl(),
    ]);

    // Render analytics charts on init so they're ready
    renderAnalytics();

    // Load app info
    elements.appVersion.textContent = '1.0.0';
    elements.appEnv.textContent = 'production';
    elements.appDb.textContent = 'MySQL';

    console.log('Dashboard initialized successfully');
}

// Start when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}