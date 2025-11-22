let currentTab = 'all';
let allLogs = [];
let lastRefreshTime = new Date();

// Initial Load
document.addEventListener('DOMContentLoaded', () => {
    fetchData();
    // Refresh every 30 minutes
    setInterval(fetchData, 30 * 60 * 1000);
    // Update "Updated X ago" every minute
    setInterval(updateTimeElapsed, 60 * 1000);
    updateTimeElapsed();
});

async function fetchData() {
    try {
        const response = await fetch('/api/logs');
        const data = await response.json();

        // Update Stats
        document.getElementById('total-emails').textContent = data.stats.total;
        document.getElementById('responded-emails').textContent = data.stats.responded;
        document.getElementById('ignored-emails').textContent = data.stats.ignored;

        // Update KB Stats
        if (data.kb_stats) {
            document.getElementById('kb-count').textContent = data.kb_stats.total_vectors;
        }

        // Store and render
        allLogs = data.logs;
        renderLogs();

        // Update timestamp
        lastRefreshTime = new Date();
        updateTimeElapsed();

    } catch (error) {
        console.error('Error fetching data:', error);
    }
}

function renderLogs() {
    const tbody = document.getElementById('logs-body');
    tbody.innerHTML = '';

    const filteredLogs = allLogs.filter(log => {
        if (currentTab === 'all') return true;
        if (currentTab === 'responded') return log.status === 'RESPONDED';
        if (currentTab === 'ignored') return log.status === 'IGNORED';
        if (currentTab === 'failed') return log.status === 'ERROR';
        return true;
    });

    filteredLogs.forEach(log => {
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
            <td style="color: var(--text-secondary); font-size: 12px;">${log.details || '-'}</td>
        `;
        tbody.appendChild(row);
    });
}

function setTab(tabName) {
    currentTab = tabName;

    // Update UI
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');

    renderLogs();
}

function updateTimeElapsed() {
    const now = new Date();
    const diffMs = now - lastRefreshTime;
    const diffMins = Math.floor(diffMs / 60000);

    const text = diffMins < 1 ? 'Just now' : `${diffMins}m ago`;
    document.getElementById('last-updated').textContent = text;
}

// File Upload Logic
function updateFileName() {
    const fileInput = document.getElementById('pdf-upload');
    const fileNameSpan = document.getElementById('file-name');
    const uploadBtn = document.getElementById('upload-btn');

    if (fileInput.files.length > 0) {
        fileNameSpan.textContent = fileInput.files[0].name;
        uploadBtn.disabled = false;
        uploadBtn.style.background = 'var(--accent-color)';
    } else {
        fileNameSpan.textContent = 'No file selected';
        uploadBtn.disabled = true;
        uploadBtn.style.background = 'var(--text-secondary)';
    }
}

async function uploadFile() {
    const fileInput = document.getElementById('pdf-upload');
    const statusDiv = document.getElementById('upload-status');
    const uploadBtn = document.getElementById('upload-btn');

    if (fileInput.files.length === 0) return;

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);

    statusDiv.textContent = '⏳ Uploading and processing...';
    statusDiv.style.color = 'var(--text-secondary)';
    uploadBtn.disabled = true;

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (response.ok) {
            statusDiv.textContent = result.message;
            statusDiv.style.color = 'var(--success-color)';
            fileInput.value = ''; // Clear input
            setTimeout(() => {
                document.getElementById('file-name').textContent = 'No file selected';
                uploadBtn.style.background = 'var(--text-secondary)';
            }, 3000);

            // Refresh data to update stats
            fetchData();
        } else {
            statusDiv.textContent = '❌ Error: ' + result.error;
            statusDiv.style.color = 'var(--error-color)';
            uploadBtn.disabled = false;
        }
    } catch (error) {
        statusDiv.textContent = '❌ Network error: ' + error.message;
        statusDiv.style.color = 'var(--error-color)';
        uploadBtn.disabled = false;
    }
}
