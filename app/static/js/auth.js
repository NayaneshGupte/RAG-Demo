/**
 * Authentication Flow Handler
 * Manages Gmail OAuth flow and auth state
 */

// Check authentication status on page load
window.addEventListener('DOMContentLoaded', async () => {
    await checkAuthStatus();

    // Check agent status if authenticated
    const isAuth = document.getElementById('dashboard-content')?.style.display !== 'none';
    if (isAuth) {
        await fetchAgentStatus();
        // Poll agent status every 10 seconds
        setInterval(fetchAgentStatus, 10000);
    }
});

/**
 * Check if user is authenticated
 */
async function checkAuthStatus() {
    try {
        const response = await fetch('/auth/status');
        const data = await response.json();

        if (data.authenticated && data.user_email) {
            showDashboard(data.user_email);
        } else {
            showAuthRequired();
        }
    } catch (error) {
        console.error('Error checking auth status:', error);
        showAuthRequired();
    }
}

/**
 * Show dashboard for authenticated user
 */
function showDashboard(userEmail) {
    const authSection = document.getElementById('auth-required');
    const dashboardSection = document.getElementById('dashboard-content');

    if (authSection) authSection.style.display = 'none';
    if (dashboardSection) {
        dashboardSection.style.display = 'block';

        // Update user email display
        const userEmailEl = document.getElementById('user-email-display');
        if (userEmailEl) {
            userEmailEl.textContent = userEmail;
        }
    }
}

/**
 * Show auth required screen
 */
function showAuthRequired() {
    const authSection = document.getElementById('auth-required');
    const dashboardSection = document.getElementById('dashboard-content');

    if (authSection) authSection.style.display = 'flex';
    if (dashboardSection) dashboardSection.style.display = 'none';
}

/**
 * Initiate Gmail OAuth login
 */
function loginWithGmail() {
    // Redirect to OAuth login endpoint
    window.location.href = '/auth/gmail/login';
}

/**
 * Logout user
 */
async function logout() {
    try {
        const response = await fetch('/auth/logout', {
            method: 'POST'
        });

        if (response.ok) {
            // Reload page to show auth screen
            window.location.reload();
        } else {
            console.error('Logout failed');
        }
    } catch (error) {
        console.error('Error during logout:', error);
    }
}

/**
 * Fetch agent status
 */
async function fetchAgentStatus() {
    try {
        const response = await fetch('/api/agent/status');
        const status = await response.json();

        updateAgentStatusUI(status);
    } catch (error) {
        console.error('Error fetching agent status:', error);
    }
}

/**
 * Update agent status UI elements
 */
function updateAgentStatusUI(status) {
    const statusDot = document.getElementById('agent-status-dot');
    const statusText = document.getElementById('agent-status-text');
    const uptimeEl = document.getElementById('agent-uptime');
    const lastPollEl = document.getElementById('agent-last-poll');
    const processedEl = document.getElementById('agent-processed');

    if (status.running) {
        if (statusDot) {
            statusDot.className = 'status-dot status-running';
        }
        if (statusText) {
            statusText.textContent = 'Agent Running';
            statusText.className = 'status-text status-running';
        }
        if (uptimeEl && status.uptime_formatted) {
            uptimeEl.textContent = status.uptime_formatted;
        }
        if (lastPollEl && status.last_poll) {
            lastPollEl.textContent = formatRelativeTime(status.last_poll);
        }
        if (processedEl) {
            processedEl.textContent = status.processed_count || 0;
        }
    } else {
        if (statusDot) {
            statusDot.className = 'status-dot status-stopped';
        }
        if (statusText) {
            if (status.error) {
                statusText.textContent = 'Error: ' + status.error;
                statusText.className = 'status-text status-error';
                statusText.style.color = '#EF4444'; // Red color for error
            } else {
                statusText.textContent = 'Agent Stopped';
                statusText.className = 'status-text status-stopped';
            }
        }
        if (uptimeEl) uptimeEl.textContent = '--';
        if (lastPollEl) lastPollEl.textContent = '--';
        if (processedEl) processedEl.textContent = '0';
    }
}

/**
 * Start agent (optional - if manual control is enabled)
 */
async function startAgent() {
    try {
        const response = await fetch('/api/agent/start', {
            method: 'POST'
        });
        const data = await response.json();

        if (data.success) {
            await fetchAgentStatus();
            showNotification('Agent started successfully', 'success');
        } else {
            showNotification(data.message || 'Failed to start agent', 'error');
        }
    } catch (error) {
        console.error('Error starting agent:', error);
        showNotification('Error starting agent', 'error');
    }
}

/**
 * Stop agent (optional - if manual control is enabled)
 */
async function stopAgent() {
    try {
        const response = await fetch('/api/agent/stop', {
            method: 'POST'
        });
        const data = await response.json();

        if (data.success) {
            await fetchAgentStatus();
            showNotification('Agent stopped', 'info');
        } else {
            showNotification(data.message || 'Failed to stop agent', 'error');
        }
    } catch (error) {
        console.error('Error stopping agent:', error);
        showNotification('Error stopping agent', 'error');
    }
}

/**
 * Format time relative to now (e.g., "2 minutes ago")
 */
function formatRelativeTime(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const secondsAgo = Math.floor((now - date) / 1000);

    if (secondsAgo < 60) return 'Just now';
    if (secondsAgo < 120) return '1 minute ago';
    if (secondsAgo < 3600) return `${Math.floor(secondsAgo / 60)} minutes ago`;
    if (secondsAgo < 7200) return '1 hour ago';
    if (secondsAgo < 86400) return `${Math.floor(secondsAgo / 3600)} hours ago`;
    return `${Math.floor(secondsAgo / 86400)} days ago`;
}

/**
 * Show notification toast (optional)
 */
function showNotification(message, type = 'info') {
    // Simple console log for now, can be enhanced with toast UI
    console.log(`[${type.toUpperCase()}] ${message}`);

    // Could add toast notification library here
    // For now, use browser alert for important messages
    if (type === 'error') {
        alert(message);
    }
}
