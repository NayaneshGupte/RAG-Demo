/**
 * Dashboard Logic
 * Handles data fetching and metric updates
 */

/**
 * Fetch dashboard data (Metrics + Charts)
 */
async function fetchData() {
    console.log('[DASHBOARD] Fetching data...');

    // Refresh charts if available
    if (window.refreshCharts) {
        window.refreshCharts();
    }

    // Fetch summary metrics
    await fetchSummaryMetrics();
}

/**
 * Fetch and update summary metrics
 */
async function fetchSummaryMetrics() {
    try {
        const response = await fetch('/api/metrics/summary');
        const data = await response.json();

        if (data.error) {
            console.error('[DASHBOARD] Error fetching summary:', data.error);
            return;
        }

        updateMetric('total-emails', data.total);
        updateMetric('responded-emails', data.responded);
        updateMetric('ignored-emails', data.ignored);

    } catch (error) {
        console.error('[DASHBOARD] Error fetching summary metrics:', error);
    }
}

/**
 * Update a single metric element
 */
function updateMetric(id, value) {
    const el = document.getElementById(id);
    if (el) {
        // Animate count up if it's a number
        const current = parseInt(el.textContent) || 0;
        const target = parseInt(value) || 0;

        if (current !== target) {
            el.textContent = target;
            // Add pulse animation class temporarily
            el.classList.add('pulse-text');
            setTimeout(() => el.classList.remove('pulse-text'), 500);
        }
    }
}

// Auto-load on start
document.addEventListener('DOMContentLoaded', () => {
    // Wait for auth check to complete (handled by auth.js)
    // But we can start fetching data immediately as the API will return empty/error if not auth
    // However, to avoid race conditions, we can wait a bit or just call it.
    // Since auth.js redirects if not auth, we are safe to call fetchData.
    fetchData();

    // Refresh every 30 seconds
    setInterval(fetchData, 30000);
});

// Expose globally
window.fetchData = fetchData;
