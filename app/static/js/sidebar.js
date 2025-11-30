/**
 * Sidebar & Theme Management
 */

// Toggle Sidebar
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');

    sidebar.classList.toggle('active');
    overlay.classList.toggle('active');

    // Prevent body scroll when sidebar is open
    if (sidebar.classList.contains('active')) {
        document.body.style.overflow = 'hidden';
    } else {
        document.body.style.overflow = '';
    }
}

// Close sidebar on escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const sidebar = document.getElementById('sidebar');
        if (sidebar && sidebar.classList.contains('active')) {
            toggleSidebar();
        }
    }
});

// Theme Management
function switchTheme(theme) {
    const root = document.documentElement;

    if (theme === 'light') {
        // Light theme colors
        root.style.setProperty('--flux-bg-primary', '#f8fafc');
        root.style.setProperty('--flux-bg-secondary', '#ffffff');
        root.style.setProperty('--flux-bg-tertiary', '#f1f5f9');

        root.style.setProperty('--flux-text-primary', '#0f172a');
        root.style.setProperty('--flux-text-secondary', '#475569');
        root.style.setProperty('--flux-text-tertiary', '#64748b');
        root.style.setProperty('--flux-text-muted', '#94a3b8');

        root.style.setProperty('--flux-glass-bg', 'rgba(255, 255, 255, 0.7)');
        root.style.setProperty('--flux-glass-border', 'rgba(0, 0, 0, 0.1)');
        root.style.setProperty('--flux-glass-hover', 'rgba(0, 0, 0, 0.05)');
    } else {
        // Dark theme colors (default)
        root.style.setProperty('--flux-bg-primary', '#0f172a');
        root.style.setProperty('--flux-bg-secondary', '#1e293b');
        root.style.setProperty('--flux-bg-tertiary', '#334155');

        root.style.setProperty('--flux-text-primary', '#ffffff');
        root.style.setProperty('--flux-text-secondary', '#94a3b8');
        root.style.setProperty('--flux-text-tertiary', '#cbd5e1');
        root.style.setProperty('--flux-text-muted', '#64748b');

        root.style.setProperty('--flux-glass-bg', 'rgba(255, 255, 255, 0.03)');
        root.style.setProperty('--flux-glass-border', 'rgba(255, 255, 255, 0.05)');
        root.style.setProperty('--flux-glass-hover', 'rgba(255, 255, 255, 0.05)');
    }

    // Store preference
    localStorage.setItem('flux-theme', theme);
}

// Load theme on page load
function loadTheme() {
    const savedTheme = localStorage.getItem('flux-theme') || 'dark';
    const themeSelect = document.getElementById('theme-select');
    if (themeSelect) {
        themeSelect.value = savedTheme;
        switchTheme(savedTheme);
    }
}

// Initialize theme on page load
document.addEventListener('DOMContentLoaded', loadTheme);

// Update sidebar metrics when main metrics are updated
function updateSidebarMetrics(total, responded, ignored) {
    const sidebarTotal = document.getElementById('sidebar-total-emails');
    const sidebarResponded = document.getElementById('sidebar-responded-emails');
    const sidebarIgnored = document.getElementById('sidebar-ignored-emails');

    if (sidebarTotal) sidebarTotal.textContent = total;
    if (sidebarResponded) sidebarResponded.textContent = responded;
    if (sidebarIgnored) sidebarIgnored.textContent = ignored;
}
