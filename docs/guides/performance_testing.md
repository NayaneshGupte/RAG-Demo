# Performance Testing Guide

This guide provides comprehensive instructions for benchmarking API and UI performance for the Flux application.

## 📋 Table of Contents

1. [Overview](#overview)
2. [API Performance Testing](#api-performance-testing)
3. [UI Performance Testing](#ui-performance-testing)
4. [Key Metrics](#key-metrics)
5. [Recommended Testing Strategy](#recommended-testing-strategy)
6. [Automated Performance Monitoring](#automated-performance-monitoring)

---

## Overview

Performance testing ensures Flux can handle expected load and provides a responsive user experience. This guide covers both backend API and frontend UI testing.

### Prerequisites

- Flux application running locally on port 5001
- Python 3.12+ environment
- Node.js (for some tools)

---

## 🚀 API Performance Testing

### 1. Apache Bench (ab) - Simple & Built-in

**Best for**: Quick baseline tests

```bash
# Test single endpoint
ab -n 1000 -c 10 http://127.0.0.1:5001/api/metrics/summary

# Options:
# -n: total requests (1000)
# -c: concurrent requests (10)
# -t: time limit in seconds

# Example: Test for 30 seconds with 50 concurrent users
ab -t 30 -c 50 http://127.0.0.1:5001/api/metrics/summary
```

**Sample Output:**
```
Requests per second:    342.15 [#/sec] (mean)
Time per request:       29.228 [ms] (mean)
Transfer rate:          156.34 [Kbytes/sec] received
```

### 2. Locust - Python-based Load Testing (Recommended)

**Best for**: Realistic user behavior simulation

#### Installation
```bash
pip install locust
```

#### Create `tests/performance/locustfile.py`

```python
from locust import HttpUser, task, between
import random

class FluxAPIUser(HttpUser):
    """Simulates a user interacting with Flux API"""
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Called when a simulated user starts"""
        # Simulate authentication if needed
        pass
    
    @task(5)  # Weight: 5 (runs 5x more often)
    def get_metrics_summary(self):
        """Get dashboard summary metrics"""
        self.client.get("/api/metrics/summary")
    
    @task(3)
    def get_email_volume(self):
        """Get email volume chart data"""
        # Random date range
        self.client.get(
            "/api/metrics/email-volume",
            params={
                "start_date": "2025-11-01",
                "end_date": "2025-11-30",
                "interval": "day"
            }
        )
    
    @task(2)
    def get_categories(self):
        """Get category distribution"""
        self.client.get("/api/metrics/categories")
    
    @task(1)
    def get_knowledge_base(self):
        """Get knowledge base documents"""
        limit = random.choice([3, 10, 20])
        self.client.get(f"/api/knowledge-base?limit={limit}")
    
    @task(1)
    def get_recent_activity(self):
        """Get recent activity logs"""
        self.client.get("/api/recent-activity?page=1")

class FluxUIUser(HttpUser):
    """Simulates a user browsing the web interface"""
    wait_time = between(2, 5)
    
    @task(3)
    def view_dashboard(self):
        self.client.get("/dashboard")
    
    @task(2)
    def view_knowledge_base(self):
        self.client.get("/knowledge-base")
    
    @task(1)
    def view_activity(self):
        self.client.get("/recent-activity")
    
    @task(1)
    def view_how_it_works(self):
        self.client.get("/how-it-works")
```

#### Run Locust Tests

**Web UI Mode** (Recommended for initial testing):
```bash
cd tests/performance
locust -f locustfile.py --host=http://127.0.0.1:5001
```
Then open http://localhost:8089 and configure:
- Number of users: 100
- Spawn rate: 10 users/second
- Duration: 5 minutes

**Headless Mode** (For CI/CD):
```bash
locust -f locustfile.py \
  --host=http://127.0.0.1:5001 \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m \
  --headless \
  --html=performance-report.html
```

### 3. k6 - Modern Load Testing

**Best for**: Advanced scenarios and grafana integration

#### Installation
```bash
# macOS
brew install k6

# Linux
sudo apt-get install k6
```

#### Create `tests/performance/api-test.js`

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');

export const options = {
  stages: [
    { duration: '30s', target: 20 },  // Ramp up to 20 users
    { duration: '1m', target: 50 },   // Ramp up to 50 users
    { duration: '2m', target: 50 },   // Stay at 50 users
    { duration: '30s', target: 0 },   // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests < 500ms
    http_req_failed: ['rate<0.01'],   // Error rate < 1%
    errors: ['rate<0.1'],
  },
};

const BASE_URL = 'http://127.0.0.1:5001';

export default function () {
  // Test summary metrics
  let res = http.get(`${BASE_URL}/api/metrics/summary`);
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 200ms': (r) => r.timings.duration < 200,
  }) || errorRate.add(1);
  
  sleep(1);
  
  // Test email volume
  res = http.get(`${BASE_URL}/api/metrics/email-volume?start_date=2025-11-01&end_date=2025-11-30`);
  check(res, {
    'email volume ok': (r) => r.status === 200,
  }) || errorRate.add(1);
  
  sleep(1);
  
  // Test categories
  res = http.get(`${BASE_URL}/api/metrics/categories`);
  check(res, {
    'categories ok': (r) => r.status === 200,
  }) || errorRate.add(1);
  
  sleep(2);
}
```

#### Run k6
```bash
k6 run tests/performance/api-test.js
```

### 4. wrk - High-Performance Benchmark

**Best for**: Maximum throughput testing

```bash
# Install
brew install wrk

# Basic test
wrk -t12 -c400 -d30s http://127.0.0.1:5001/api/metrics/summary

# With Lua script for POST requests
wrk -t12 -c400 -d30s -s post.lua http://127.0.0.1:5001/api/upload
```

---

## 🎨 UI Performance Testing

### 1. Lighthouse - Google's Performance Auditor

**Best for**: Overall web performance audit

#### Chrome DevTools Method
1. Open Chrome DevTools (F12)
2. Navigate to "Lighthouse" tab
3. Select categories: Performance, Best Practices, SEO, Accessibility
4. Click "Analyze page load"

#### CLI Method
```bash
# Install
npm install -g lighthouse

# Test dashboard
lighthouse http://127.0.0.1:5001/dashboard --view

# Generate reports for all pages
lighthouse http://127.0.0.1:5001/ --output json html --output-path ./reports/landing
lighthouse http://127.0.0.1:5001/dashboard --output json html --output-path ./reports/dashboard
lighthouse http://127.0.0.1:5001/knowledge-base --output json html --output-path ./reports/kb
```

### 2. Chrome DevTools Performance Profiling

**Manual Performance Analysis:**

1. Open DevTools → Performance tab
2. Click "Record" (Ctrl/Cmd + E)
3. Interact with your app:
   - Navigate between pages
   - Click buttons
   - Scroll through content
4. Stop recording
5. Analyze:
   - **Loading**: Time to first paint, DOM content loaded
   - **Scripting**: JavaScript execution time
   - **Rendering**: Layout, paint times
   - **Network**: Request waterfall

**Key Areas to Check:**
- Long tasks (> 50ms)
- Forced synchronous layouts
- Excessive DOM size
- JavaScript parse/compile time

### 3. WebPageTest - Comprehensive Analysis

**Best for**: Real-world performance from different locations

1. Visit https://www.webpagetest.org/
2. For local testing, use ngrok:
   ```bash
   # Install ngrok
   brew install ngrok
   
   # Expose local server
   ngrok http 5001
   
   # Use the https URL in WebPageTest
   ```
3. Configure test:
   - Location: Choose nearest test location
   - Browser: Chrome
   - Connection: Cable or Mobile 4G
4. Analyze results:
   - Filmstrip view
   - Request waterfall
   - Optimization suggestions

### 4. Playwright - Automated UI Performance

**Best for**: Continuous performance monitoring

#### Installation
```bash
pip install playwright
playwright install
```

#### Create `tests/performance/ui_performance_test.py`

```python
from playwright.sync_api import sync_playwright
import time
import json

def test_page_performance(url, page_name):
    """Test performance metrics for a specific page"""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        # Start timing
        start = time.time()
        
        # Navigate to page
        page.goto(url)
        
        # Wait for key elements based on page
        if 'dashboard' in url:
            page.wait_for_selector('#total-emails')
            page.wait_for_selector('#email-volume-chart')
        elif 'knowledge-base' in url:
            page.wait_for_selector('.kb-document')
        
        # End timing
        load_time = time.time() - start
        
        # Get performance metrics
        metrics = page.evaluate('''() => {
            const perfData = window.performance.timing;
            const paintEntries = performance.getEntriesByType('paint');
            
            return {
                // Navigation timing
                domContentLoaded: perfData.domContentLoadedEventEnd - perfData.navigationStart,
                loadComplete: perfData.loadEventEnd - perfData.navigationStart,
                domInteractive: perfData.domInteractive - perfData.navigationStart,
                
                // Paint timing
                firstPaint: paintEntries[0] ? paintEntries[0].startTime : 0,
                firstContentfulPaint: paintEntries[1] ? paintEntries[1].startTime : 0,
                
                // Resource timing
                totalResources: performance.getEntriesByType('resource').length,
                
                // Memory (if available)
                jsHeapSize: performance.memory ? performance.memory.usedJSHeapSize : 0
            };
        }''')
        
        # Print results
        print(f"\n{'='*60}")
        print(f"Performance Test: {page_name}")
        print(f"{'='*60}")
        print(f"Total Load Time:        {load_time:.2f}s")
        print(f"DOM Content Loaded:     {metrics['domContentLoaded']}ms")
        print(f"Load Complete:          {metrics['loadComplete']}ms")
        print(f"DOM Interactive:        {metrics['domInteractive']}ms")
        print(f"First Paint:            {metrics['firstPaint']:.2f}ms")
        print(f"First Contentful Paint: {metrics['firstContentfulPaint']:.2f}ms")
        print(f"Total Resources:        {metrics['totalResources']}")
        if metrics['jsHeapSize']:
            print(f"JS Heap Size:           {metrics['jsHeapSize'] / 1024 / 1024:.2f} MB")
        
        # Save to JSON
        result = {
            'page': page_name,
            'url': url,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'load_time': load_time,
            'metrics': metrics
        }
        
        with open(f'performance_{page_name}.json', 'w') as f:
            json.dump(result, f, indent=2)
        
        browser.close()
        return result

def run_all_tests():
    """Run performance tests for all key pages"""
    BASE_URL = 'http://127.0.0.1:5001'
    
    pages = [
        ('/', 'landing'),
        ('/dashboard', 'dashboard'),
        ('/knowledge-base', 'knowledge-base'),
        ('/recent-activity', 'recent-activity'),
        ('/how-it-works', 'how-it-works'),
    ]
    
    results = []
    for path, name in pages:
        result = test_page_performance(f'{BASE_URL}{path}', name)
        results.append(result)
        time.sleep(2)  # Wait between tests
    
    # Generate summary
    print(f"\n{'='*60}")
    print("PERFORMANCE SUMMARY")
    print(f"{'='*60}")
    for result in results:
        print(f"{result['page']:20} | Load: {result['load_time']:.2f}s | FCP: {result['metrics']['firstContentfulPaint']:.0f}ms")

if __name__ == "__main__":
    run_all_tests()
```

#### Run Tests
```bash
python tests/performance/ui_performance_test.py
```

---

## 📊 Key Metrics to Track

### API Performance Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| **Response Time (p50)** | < 100ms | Median response time |
| **Response Time (p95)** | < 300ms | 95th percentile |
| **Response Time (p99)** | < 500ms | 99th percentile |
| **Throughput** | > 100 RPS | Requests per second |
| **Error Rate** | < 1% | Failed request percentage |
| **Concurrent Users** | > 50 | Maximum simultaneous users |

### UI Performance Metrics (Core Web Vitals)

| Metric | Good | Needs Improvement | Poor |
|--------|------|-------------------|------|
| **LCP** (Largest Contentful Paint) | < 2.5s | 2.5s - 4.0s | > 4.0s |
| **FID** (First Input Delay) | < 100ms | 100ms - 300ms | > 300ms |
| **CLS** (Cumulative Layout Shift) | < 0.1 | 0.1 - 0.25 | > 0.25 |
| **FCP** (First Contentful Paint) | < 1.8s | 1.8s - 3.0s | > 3.0s |
| **TTI** (Time to Interactive) | < 3.8s | 3.8s - 7.3s | > 7.3s |
| **TBT** (Total Blocking Time) | < 200ms | 200ms - 600ms | > 600ms |
| **Speed Index** | < 3.4s | 3.4s - 5.8s | > 5.8s |

---

## 🎯 Recommended Testing Strategy

### 1. Quick Baseline Test (5 minutes)

```bash
# API quick test
ab -n 100 -c 10 http://127.0.0.1:5001/api/metrics/summary

# UI quick test
lighthouse http://127.0.0.1:5001/dashboard --view
```

### 2. Comprehensive Load Test (30 minutes)

```bash
# Create directory
mkdir -p tests/performance && cd tests/performance

# Run Locust comprehensive test
locust -f locustfile.py \
  --host=http://127.0.0.1:5001 \
  --users 100 \
  --spawn-rate 10 \
  --run-time 10m \
  --headless \
  --html=locust-report.html
```

### 3. Full Performance Audit (1 hour)

```bash
# 1. API load testing with multiple scenarios
k6 run api-test.js

# 2. UI performance for all pages
python ui_performance_test.py

# 3. Lighthouse for all pages
lighthouse http://127.0.0.1:5001/ --output html --output-path ./reports/landing.html
lighthouse http://127.0.0.1:5001/dashboard --output html --output-path ./reports/dashboard.html
lighthouse http://127.0.0.1:5001/knowledge-base --output html --output-path ./reports/kb.html

# 4. Generate combined report
# (Use custom script or manually analyze)
```

---

## 🤖 Automated Performance Monitoring

### CI/CD Integration

#### GitHub Actions Example

Create `.github/workflows/performance.yml`:

```yaml
name: Performance Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday

jobs:
  performance-test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install locust playwright
          playwright install
      
      - name: Start Flux server
        run: |
          python wsgi.py &
          sleep 10
      
      - name: Run API performance tests
        run: |
          locust -f tests/performance/locustfile.py \
            --host=http://localhost:5001 \
            --users 50 \
            --spawn-rate 5 \
            --run-time 2m \
            --headless \
            --html=locust-report.html
      
      - name: Run UI performance tests
        run: python tests/performance/ui_performance_test.py
      
      - name: Upload performance reports
        uses: actions/upload-artifact@v3
        with:
          name: performance-reports
          path: |
            locust-report.html
            performance_*.json
```

### Performance Budgets

Create `performance-budgets.json`:

```json
{
  "api": {
    "response_time_p95": 300,
    "response_time_p99": 500,
    "error_rate": 0.01,
    "min_throughput": 100
  },
  "ui": {
    "lcp": 2500,
    "fcp": 1800,
    "tti": 3800,
    "cls": 0.1,
    "tbt": 200
  }
}
```

### Monitoring Script

Create `tests/performance/monitor.py`:

```python
import json
import subprocess
import sys

def check_budgets():
    """Check if performance metrics meet budgets"""
    with open('performance-budgets.json') as f:
        budgets = json.load(f)
    
    # Check API metrics (from Locust or k6 output)
    # Check UI metrics (from Lighthouse/Playwright output)
    
    violations = []
    
    # Example check
    # if actual_lcp > budgets['ui']['lcp']:
    #     violations.append(f"LCP exceeded budget: {actual_lcp}ms > {budgets['ui']['lcp']}ms")
    
    if violations:
        print("❌ Performance budget violations:")
        for v in violations:
            print(f"  - {v}")
        sys.exit(1)
    else:
        print("✅ All performance budgets met!")
        sys.exit(0)

if __name__ == "__main__":
    check_budgets()
```

---

## 📈 Analyzing Results

### What to Look For

**API Performance:**
- Slow endpoints (> 500ms p95)
- High error rates (> 1%)
- Memory leaks (increasing over time)
- Database bottlenecks

**UI Performance:**
- Large JavaScript bundles
- Unoptimized images
- Render-blocking resources
- Layout shifts
- Long tasks blocking main thread

### Optimization Checklist

- [ ] Enable gzip compression for API responses
- [ ] Implement API response caching
- [ ] Optimize database queries (add indexes)
- [ ] Minify CSS/JS
- [ ] Optimize images (WebP format)
- [ ] Implement lazy loading for charts
- [ ] Use CDN for static assets
- [ ] Enable HTTP/2
- [ ] Implement service workers for caching

---

## 🔗 Further Reading

- [Web Vitals](https://web.dev/vitals/)
- [Lighthouse CI](https://github.com/GoogleChrome/lighthouse-ci)
- [k6 Documentation](https://k6.io/docs/)
- [Locust Documentation](https://docs.locust.io/)
- [Playwright Performance Testing](https://playwright.dev/docs/api/class-page#page-evaluate)

---

**Last Updated**: November 30, 2025
