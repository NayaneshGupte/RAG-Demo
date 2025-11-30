let currentTab = 'all';
let allLogs = [];
let lastRefreshTime = new Date();
let currentPage = 1;
const itemsPerPage = 5;

// Initial Load
document.addEventListener('DOMContentLoaded', () => {
    fetchData();

    // Listen to date range changes
    DateRangeManager.onChange((params) => {
        console.log('Date range changed in activity:', params);
        fetchData();
    });

    // Refresh every 30 minutes
    setInterval(fetchData, 30 * 60 * 1000);
    // Update "Updated X ago" every minute
    setInterval(updateTimeElapsed, 60 * 1000);
    updateTimeElapsed();
});

async function fetchData() {
    try {
        // Get date range from shared manager
        const dateParams = DateRangeManager.getParams();
        const url = `/api/logs?start_date=${dateParams.start_date}&end_date=${dateParams.end_date}`;

        const response = await fetch(url);
        const data = await response.json();

        console.log('Fetched data:', data);

        // Update Stats (with null checks for elements that may not exist on all pages)
        const totalEmailsEl = document.getElementById('total-emails');
        const respondedEmailsEl = document.getElementById('responded-emails');
        const ignoredEmailsEl = document.getElementById('ignored-emails');

        if (totalEmailsEl) totalEmailsEl.textContent = data.stats.total;
        if (respondedEmailsEl) respondedEmailsEl.textContent = data.stats.responded;
        if (ignoredEmailsEl) ignoredEmailsEl.textContent = data.stats.ignored;

        // Update KB Stats (only if element exists)
        if (data.kb_stats) {
            const kbCountEl = document.getElementById('kb-count');
            if (kbCountEl) {
                kbCountEl.textContent = data.kb_stats.total_vectors;
            }
        }

        // Store and render
        allLogs = data.logs;
        renderLogs();

        // Update timestamp
        lastRefreshTime = new Date();
        updateTimeElapsed();

        // Refresh charts if available
        if (window.refreshCharts) {
            window.refreshCharts();
        }

    } catch (error) {
        console.error('Error fetching data:', error);
    }
}

function renderLogs() {
    const tbody = document.getElementById('logs-body');

    if (!tbody) {
        // Silent return - we might be on the dashboard where table doesn't exist
        return;
    }

    tbody.innerHTML = '';

    console.log('Rendering logs:', allLogs.length, 'total,', 'current tab:', currentTab);

    const filteredLogs = allLogs.filter(log => {
        if (currentTab === 'all') return true;
        if (currentTab === 'responded') return log.status === 'RESPONDED';
        if (currentTab === 'ignored') return log.status === 'IGNORED';
        if (currentTab === 'failed') return log.status === 'ERROR';
        return true;
    });

    console.log('Filtered logs:', filteredLogs.length);

    if (filteredLogs.length === 0) {
        const emptyRow = document.createElement('tr');
        emptyRow.innerHTML = '<td colspan="7" style="text-align: center; padding: 40px; color: var(--flux-text-muted);">No activity logs found</td>';
        tbody.appendChild(emptyRow);
        // Render empty pagination
        renderPagination(0);
        return;
    }

    // Pagination: slice logs for current page
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const paginatedLogs = filteredLogs.slice(startIndex, endIndex);

    console.log(`Showing page ${currentPage}: items ${startIndex + 1}-${Math.min(endIndex, filteredLogs.length)} of ${filteredLogs.length}`);

    paginatedLogs.forEach(log => {
        const row = document.createElement('tr');

        // Format timestamps
        const emailTime = log.email_timestamp ? new Date(log.email_timestamp).toLocaleString() : '-';
        const responseTime = log.timestamp ? new Date(log.timestamp).toLocaleString() : '-';

        // Determine badge class
        let badgeClass = 'status-ignored';
        if (log.status === 'RESPONDED') badgeClass = 'status-responded';
        if (log.status === 'ERROR') badgeClass = 'status-error';

        row.innerHTML = `
            <td>${emailTime}</td>
            <td>${responseTime}</td>
            <td><span class="status-badge ${badgeClass}">${log.status}</span></td>
            <td>${log.sender || 'Unknown'}</td>
            <td>${log.subject}</td>
            <td>${log.category || '-'}</td>
            <td style="color: var(--flux-text-secondary); font-size: 12px;">${log.details || '-'}</td>
        `;
        tbody.appendChild(row);
    });

    // Render pagination
    renderPagination(filteredLogs.length);
}

function renderPagination(totalItems) {
    const paginationContainer = document.getElementById('pagination-controls');

    if (!paginationContainer) return;

    const totalPages = Math.ceil(totalItems / itemsPerPage);

    // Hide pagination if only one page
    if (totalPages <= 1) {
        paginationContainer.innerHTML = '';
        paginationContainer.style.display = 'none';
        return;
    }

    paginationContainer.style.display = 'flex';

    let paginationHTML = `
        <button class="pagination-btn" onclick="changePage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>
            ← Previous
        </button>
        <div class="pagination-info">
            Page ${currentPage} of ${totalPages} (${totalItems} items)
        </div>
        <button class="pagination-btn" onclick="changePage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}>
            Next →
        </button>
    `;

    paginationContainer.innerHTML = paginationHTML;
}

function changePage(newPage) {
    const filteredLogs = allLogs.filter(log => {
        if (currentTab === 'all') return true;
        if (currentTab === 'responded') return log.status === 'RESPONDED';
        if (currentTab === 'ignored') return log.status === 'IGNORED';
        if (currentTab === 'failed') return log.status === 'ERROR';
        return true;
    });

    const totalPages = Math.ceil(filteredLogs.length / itemsPerPage);

    if (newPage < 1 || newPage > totalPages) return;

    currentPage = newPage;
    renderLogs();
}

function setTab(tabName) {
    currentTab = tabName;
    currentPage = 1; // Reset to first page when changing tabs

    // Update active tab styling
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');

    renderLogs();
}

function updateTimeElapsed() {
    const lastUpdatedEl = document.getElementById('last-updated');
    if (!lastUpdatedEl) return;

    const now = new Date();
    const diffMs = now - lastRefreshTime;
    const diffMins = Math.floor(diffMs / 60000);

    const text = diffMins < 1 ? 'Just now' : `${diffMins}m ago`;
    lastUpdatedEl.textContent = text;
}

// File upload logic moved to knowledge-base.js

// Date picker helper functions for recent-activity page
let datePickerInstance = null;

function loadSavedDateRange() {
    try {
        const preset = DateRangeManager.getCurrentPreset();
        const custom = DateRangeManager.getCurrentCustom();
        const dropdown = document.getElementById('dateRangeDropdown');
        if (dropdown) {
            dropdown.value = preset;
            if (preset === 'custom' && custom) showCustomDatePicker();
        }
    } catch (error) {
        console.error('Error loading saved date range:', error);
    }
}

function initDatePicker() {
    const input = document.getElementById('customDatePicker');
    if (!input || typeof flatpickr === 'undefined') return;
    datePickerInstance = flatpickr(input, {
        mode: 'range',
        dateFormat: 'Y-m-d',
        theme: 'dark',
        maxDate: 'today',
        onChange: function (selectedDates) {
            if (selectedDates.length === 2) {
                const diffTime = Math.abs(selectedDates[1] - selectedDates[0]);
                const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
                if (diffDays > 366) {
                    alert('Date range cannot exceed 12 months');
                    datePickerInstance.clear();
                    return;
                }
                const customDates = {
                    start: selectedDates[0].toISOString().split('T')[0],
                    end: selectedDates[1].toISOString().split('T')[0]
                };
                DateRangeManager.setRange('custom', customDates);
            }
        }
    });
    const custom = DateRangeManager.getCurrentCustom();
    if (custom) datePickerInstance.setDate([custom.start, custom.end]);
}

function showCustomDatePicker() {
    const customRange = document.getElementById('customDateRange');
    if (customRange) {
        customRange.style.display = 'block';
        if (!datePickerInstance) initDatePicker();
    }
}

function hideCustomDatePicker() {
    const customRange = document.getElementById('customDateRange');
    if (customRange) customRange.style.display = 'none';
}

function handleDateRangeChange() {
    const dropdown = document.getElementById('dateRangeDropdown');
    if (!dropdown) return;
    const value = dropdown.value;
    if (value === 'custom') {
        showCustomDatePicker();
        const custom = DateRangeManager.getCurrentCustom();
        if (custom) DateRangeManager.setRange('custom', custom);
    } else {
        hideCustomDatePicker();
        DateRangeManager.setRange(value, null);
    }
}

// Initialize date picker
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        loadSavedDateRange();
        initDatePicker();
    });
} else {
    loadSavedDateRange();
    initDatePicker();
}
