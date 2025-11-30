/**
 * Authentication Flow Handler
 * Manages Gmail OAuth flow and auth state
 */

// Check authentication status on page load
window.addEventListener('DOMContentLoaded', async () => {
    await checkAuthStatus();

    // Check agent status if on dashboard
    const isDashboard = !!document.getElementById('dashboard-content');
    if (isDashboard) {
        await fetchAgentStatus();
        // Poll agent status every 10 seconds
        setInterval(fetchAgentStatus, 10000);
    }
});

/**
 * Check if user is authenticated
 */
/**
 * Check if user is authenticated and handle redirects
 */
async function checkAuthStatus() {
    try {
        const response = await fetch('/auth/status');
        const data = await response.json();
        const currentPath = window.location.pathname;
        const urlParams = new URLSearchParams(window.location.search);
        const showLanding = urlParams.get('show_landing') === 'true';

        if (data.authenticated && data.user_email) {
            // User is authenticated
            if ((currentPath === '/' || currentPath === '/index.html') && !showLanding) {
                window.location.href = '/dashboard';
            } else {
                // Already on dashboard or other protected page, initialize UI
                if (currentPath !== '/' && currentPath !== '/index.html') {
                    initializeDashboard(data.user_email);
                }
            }
        } else {
            // User is NOT authenticated
            // Allow access to public pages: /, /how-it-works, /auth/*
            const publicPages = ['/', '/index.html', '/how-it-works'];
            const isPublicPage = publicPages.includes(currentPath) || currentPath.startsWith('/auth/');

            if (!isPublicPage) {
                // Redirect to landing page if trying to access protected route
                window.location.href = '/';
            }
        }
    } catch (error) {
        console.error('Error checking auth status:', error);
        if (window.location.pathname !== '/') {
            window.location.href = '/';
        }
    }
}

/**
 * Initialize dashboard UI for authenticated user
 */
function initializeDashboard(userEmail) {
    // Update user email display
    const userEmailEl = document.getElementById('user-email-sidebar');
    if (userEmailEl) {
        userEmailEl.textContent = userEmail;
    }

    // Store demo flag if it's a demo user
    if (userEmail === 'demo@example.com') {
        sessionStorage.setItem('is_demo', 'true');
    }
}

/**
 * Show auth required screen (Deprecated - handled by redirect)
 */
function showAuthRequired() {
    // No-op
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
/**
 * Logout user (handles both regular and demo users)
 */
async function logout() {
    try {
        // Check if demo mode (check session first)
        const isDemo = sessionStorage.getItem('is_demo') === 'true';
        const logoutEndpoint = isDemo ? '/auth/demo/logout' : '/auth/logout';

        const response = await fetch(logoutEndpoint, {
            method: 'POST'
        });

        if (response.ok) {
            // Close sidebar if it's open
            const sidebar = document.getElementById('sidebar');
            const overlay = document.getElementById('sidebar-overlay');
            if (sidebar) sidebar.classList.remove('active');
            if (overlay) overlay.classList.remove('active');

            // Clear session storage
            sessionStorage.clear();

            // Prevent back navigation by replacing history
            if (window.history && window.history.replaceState) {
                // Replace current state to prevent going back
                window.history.replaceState(null, '', '/');
            }

            // Force reload to ensure clean state and proper auth check
            window.location.reload();

            // Add extra protection: listen for popstate to prevent back
            window.addEventListener('popstate', function preventBack(e) {
                window.history.pushState(null, '', '/');
                window.removeEventListener('popstate', preventBack);
            });
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
