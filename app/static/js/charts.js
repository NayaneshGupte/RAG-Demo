let emailVolumeChartInstance = null;
let categoryChartInstance = null;
let chartDatePickerInstance = null;

/**
 * Load saved date range and update dropdown
 */
function loadSavedDateRange() {
    try {
        const preset = DateRangeManager.getCurrentPreset();
        const custom = DateRangeManager.getCurrentCustom();

        // Update dropdown
        const dropdown = document.getElementById('dateRangeDropdown');
        if (dropdown) {
            dropdown.value = preset;

            // If custom range is active, show date picker
            if (preset === 'custom' && custom) {
                showCustomDatePicker();
            }
        }
    } catch (error) {
        console.error('Error loading saved date range:', error);
    }
}

/**
 * Initialize Flatpickr date picker
 */
function initDatePicker() {
    const input = document.getElementById('customDatePicker');
    if (!input || typeof flatpickr === 'undefined') return;

    chartDatePickerInstance = flatpickr(input, {
        mode: 'range',
        dateFormat: 'Y-m-d',
        theme: 'dark',
        maxDate: 'today',
        onChange: function (selectedDates) {
            if (selectedDates.length === 2) {
                // Check if range exceeds 12 months (366 days to be safe)
                const diffTime = Math.abs(selectedDates[1] - selectedDates[0]);
                const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

                if (diffDays > 366) {
                    alert('Date range cannot exceed 12 months');
                    chartDatePickerInstance.clear();
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

    // Set initial dates if custom range exists
    const custom = DateRangeManager.getCurrentCustom();
    if (custom) {
        chartDatePickerInstance.setDate([custom.start, custom.end]);
    }
}

/**
 * Show custom date picker
 */
function showCustomDatePicker() {
    const customRange = document.getElementById('customDateRange');
    if (customRange) {
        customRange.style.display = 'block';
        if (!chartDatePickerInstance) {
            initDatePicker();
        }
    }
}

/**
 * Hide custom date picker
 */
function hideCustomDatePicker() {
    const customRange = document.getElementById('customDateRange');
    if (customRange) {
        customRange.style.display = 'none';
    }
}

/**
 * Handle date range dropdown change
 */
function handleDateRangeChange() {
    const dropdown = document.getElementById('dateRangeDropdown');
    if (!dropdown) return;

    const value = dropdown.value;

    if (value === 'custom') {
        showCustomDatePicker();
        // Only set if custom dates already selected
        const custom = DateRangeManager.getCurrentCustom();
        if (custom) {
            DateRangeManager.setRange('custom', custom);
        }
    } else {
        hideCustomDatePicker();
        DateRangeManager.setRange(value, null);
    }
}

/**
 * Initialize Email Volume Chart with ApexCharts
 */
function initEmailVolumeChart(data) {
    const chartElement = document.getElementById('emailVolumeChart');
    if (!chartElement) {
        console.error('[CHARTS] emailVolumeChart element not found');
        return null;
    }

    // Destroy existing chart if it exists
    if (emailVolumeChartInstance) {
        emailVolumeChartInstance.destroy();
    }

    const options = {
        series: [
            {
                name: 'Total',
                data: data.total || []
            },
            {
                name: 'Responded',
                data: data.responded || []
            },
            {
                name: 'Ignored',
                data: data.ignored || []
            },
            {
                name: 'Failed',
                data: data.failed || []
            }
        ],
        chart: {
            type: 'line',
            height: '100%',
            background: 'transparent',
            toolbar: {
                show: false
            },
            zoom: {
                enabled: false
            }
        },
        colors: ['#818cf8', '#34d399', '#fbbf24', '#ef4444'],
        dataLabels: {
            enabled: false
        },
        stroke: {
            curve: 'smooth',
            width: 2
        },
        xaxis: {
            categories: data.labels || [],
            labels: {
                style: {
                    colors: '#94a3b8',
                    fontSize: '11px',
                    fontFamily: 'Inter'
                }
            },
            axisBorder: {
                show: false
            },
            axisTicks: {
                show: false
            }
        },
        yaxis: {
            labels: {
                style: {
                    colors: '#94a3b8',
                    fontSize: '11px',
                    fontFamily: 'Inter'
                }
            }
        },
        grid: {
            borderColor: 'rgba(255, 255, 255, 0.05)',
            strokeDashArray: 0
        },
        legend: {
            position: 'bottom',
            horizontalAlign: 'center',
            labels: {
                colors: '#94a3b8'
            },
            markers: {
                radius: 12
            },
            itemMargin: {
                horizontal: 15
            }
        },
        tooltip: {
            theme: 'dark',
            style: {
                fontSize: '13px',
                fontFamily: 'Inter'
            }
        }
    };

    emailVolumeChartInstance = new ApexCharts(chartElement, options);
    emailVolumeChartInstance.render();
    console.log('[CHARTS] Email volume chart rendered');
    return emailVolumeChartInstance;
}

/**
 * Initialize Category Breakdown Chart with ApexCharts
 */
function initCategoryChart(data) {
    const chartElement = document.getElementById('categoryChart');
    if (!chartElement) {
        console.error('[CHARTS] categoryChart element not found');
        return null;
    }

    // Destroy existing chart if it exists
    if (categoryChartInstance) {
        categoryChartInstance.destroy();
    }

    const options = {
        series: data.values || [],
        chart: {
            type: 'donut',
            height: '100%',
            background: 'transparent'
        },
        colors: ['#818cf8', '#34d399', '#fbbf24', '#f472b6', '#60a5fa'],
        labels: data.labels || [],
        dataLabels: {
            enabled: true,
            style: {
                fontSize: '12px',
                fontFamily: 'Inter',
                fontWeight: 600
            }
        },
        legend: {
            position: 'right',
            labels: {
                colors: '#94a3b8'
            },
            markers: {
                radius: 12
            }
        },
        plotOptions: {
            pie: {
                donut: {
                    size: '65%'
                }
            }
        },
        tooltip: {
            theme: 'dark',
            style: {
                fontSize: '13px',
                fontFamily: 'Inter'
            }
        },
        stroke: {
            width: 2,
            colors: ['#0f172a']
        }
    };

    categoryChartInstance = new ApexCharts(chartElement, options);
    categoryChartInstance.render();
    console.log('[CHARTS] Category chart rendered');
    return categoryChartInstance;
}

/**
 * Fetch and render email volume data
 */
async function renderEmailVolumeChart() {
    try {
        const dateParams = DateRangeManager.getParams();
        const url = `/api/metrics/email-volume?start_date=${dateParams.start_date}&end_date=${dateParams.end_date}&interval=${dateParams.interval}`;
        console.log('[CHARTS] Fetching email volume from:', url);

        const response = await fetch(url);
        const data = await response.json();
        console.log('[CHARTS] Email volume data received:', data);

        if (data.error) {
            console.error('[CHARTS] API Error:', data.error);
            return;
        }

        initEmailVolumeChart(data);
    } catch (error) {
        console.error('[CHARTS] Error fetching email volume data:', error);
    }
}

/**
 * Fetch and render category breakdown
 */
async function renderCategoryChart() {
    try {
        console.log('[CHARTS] Fetching category metrics...');
        const response = await fetch('/api/metrics/categories');
        const data = await response.json();
        console.log('[CHARTS] Category data received:', data);

        if (data.error) {
            console.error('[CHARTS] API Error:', data.error);
            return;
        }

        initCategoryChart(data);
    } catch (error) {
        console.error('[CHARTS] Error fetching category data:', error);
    }
}

/**
 * Initialize all charts
 */
function initializeCharts() {
    console.log('[CHARTS] initializeCharts called');
    console.log('[CHARTS] ApexCharts type:', typeof ApexCharts);
    console.log('[CHARTS] DateRangeManager type:', typeof DateRangeManager);

    // Check if ApexCharts is loaded
    if (typeof ApexCharts === 'undefined') {
        console.error('[CHARTS] ApexCharts not loaded');
        return;
    }
    console.log('[CHARTS] ApexCharts loaded ✓');

    // Check if DateRangeManager is loaded
    if (typeof DateRangeManager === 'undefined') {
        console.error('[CHARTS] DateRangeManager not loaded');
        return;
    }
    console.log('[CHARTS] DateRangeManager loaded ✓');

    // Load saved date range
    console.log('[CHARTS] Loading saved date range...');
    loadSavedDateRange();

    // Listen to date range changes
    console.log('[CHARTS] Setting up date range change listener...');
    DateRangeManager.onChange((params) => {
        console.log('[CHARTS] Date range changed:', params);
        renderEmailVolumeChart();
    });

    console.log('[CHARTS] Rendering charts...');
    renderEmailVolumeChart();
    renderCategoryChart();
    console.log('[CHARTS] Initialization complete');
}

// Expose refresh function globally
window.refreshCharts = function () {
    console.log('[CHARTS] Manual refresh triggered');
    renderEmailVolumeChart();
    renderCategoryChart();
};

// Expose handleDateRangeChange globally for onclick handler
window.handleDateRangeChange = handleDateRangeChange;

// Auto-initialize when DOM is ready
console.log('[CHARTS] charts.js loaded, document state:', document.readyState);
if (document.readyState === 'loading') {
    console.log('[CHARTS] Waiting for DOMContentLoaded...');
    document.addEventListener('DOMContentLoaded', initializeCharts);
} else {
    console.log('[CHARTS] DOM already ready, initializing immediately...');
    initializeCharts();
}
