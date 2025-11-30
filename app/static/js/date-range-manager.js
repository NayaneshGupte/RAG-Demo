/**
 * Shared Date Range Manager
 * Manages date range selection across Dashboard and Recent Activity pages
 * Persists state in localStorage for seamless navigation
 */

const DateRangeManager = (() => {
    const STORAGE_KEY = 'flux_date_range';

    // Default state
    let state = {
        preset: '7d',
        custom: null
    };

    // Event listeners
    const listeners = [];

    /**
     * Load state from localStorage
     */
    function loadState() {
        try {
            const saved = localStorage.getItem(STORAGE_KEY);
            if (saved) {
                state = JSON.parse(saved);
            }
        } catch (error) {
            console.error('Error loading date range state:', error);
        }
    }

    /**
     * Save state to localStorage
     */
    function saveState() {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
        } catch (error) {
            console.error('Error saving date range state:', error);
        }
    }

    /**
     * Calculate interval based on duration
     */
    function calculateInterval(diffDays) {
        if (diffDays <= 30) return 'day';
        if (diffDays <= 180) return 'week';
        return 'month';
    }

    /**
     * Get date range parameters for API calls
     */
    function getParams() {
        let start, end, interval = 'day';

        if (state.preset === 'custom' && state.custom) {
            start = new Date(state.custom.start);
            end = new Date(state.custom.end);

            const diffTime = Math.abs(end - start);
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            interval = calculateInterval(diffDays);

            return {
                start_date: state.custom.start,
                end_date: state.custom.end,
                interval: interval
            };
        }

        // Calculate preset ranges
        end = new Date();
        start = new Date();

        switch (state.preset) {
            case 'today':
                // Today only
                interval = 'day';
                break;
            case '7d':
                start.setDate(start.getDate() - 7);
                interval = 'day';
                break;
            case '1m':
                start.setMonth(start.getMonth() - 1);
                interval = 'day';
                break;
            case '3m':
                start.setMonth(start.getMonth() - 3);
                interval = 'week';
                break;
            case '6m':
                start.setMonth(start.getMonth() - 6);
                interval = 'week';
                break;
            case '12m':
                start.setFullYear(start.getFullYear() - 1);
                interval = 'month';
                break;
        }

        return {
            start_date: start.toISOString().split('T')[0],
            end_date: end.toISOString().split('T')[0],
            interval: interval
        };
    }

    /**
     * Set date range and notify listeners
     */
    function setRange(preset, customDates = null) {
        state.preset = preset;
        state.custom = customDates;
        saveState();
        notifyListeners();
    }

    /**
     * Register a change listener
     */
    function onChange(callback) {
        listeners.push(callback);
    }

    /**
     * Notify all listeners of state change
     */
    function notifyListeners() {
        const params = getParams();
        listeners.forEach(callback => callback(params));
    }

    /**
     * Get current preset value
     */
    function getCurrentPreset() {
        return state.preset;
    }

    /**
     * Get current custom dates
     */
    function getCurrentCustom() {
        return state.custom;
    }

    /**
     * Initialize on module load
     */
    function init() {
        loadState();
    }

    // Public API
    return {
        init,
        getParams,
        setRange,
        onChange,
        getCurrentPreset,
        getCurrentCustom
    };
})();

// Auto-initialize
DateRangeManager.init();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DateRangeManager;
}
