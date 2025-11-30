# Test Execution Guide

## Setup

1. **Install test dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Verify installation:**
   ```bash
   pytest --version
   ```

## Running Tests

### Run all tests
```bash
pytest
```

### Run with coverage report
```bash
pytest --cov=app --cov-report=html
```

### Run specific test file
```bash
pytest tests/unit/test_database_service.py
```

### Run specific test class
```bash
pytest tests/unit/test_database_service.py::TestEmailLogging
```

### Run specific test function
```bash
pytest tests/unit/test_database_service.py::TestEmailLogging::test_log_email_basic
```

### Run only unit tests
```bash
pytest tests/unit/
```

### Run only integration tests
```bash
pytest tests/integration/
```

### Run with verbose output
```bash
pytest -v
```

### Run and stop on first failure
```bash
pytest -x
```

### Run tests in parallel (faster)
```bash
pytest -n auto
```

## Coverage Reports

### Generate HTML coverage report
```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html  # macOS
```

### View coverage in terminal
```bash
pytest --cov=app --cov-report=term-missing
```

### Generate coverage badge
```bash
pytest --cov=app --cov-report=term --cov-report=html
```

## Test Organization

```
tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Unit tests
│   └── test_database_service.py
├── integration/             # Integration tests
│   ├── test_api_routes.py
│   └── test_auth_routes.py
└── fixtures/                # Test data
```

## Continuous Integration

Add to `.github/workflows/tests.yml`:
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: pytest --cov=app --cov-report=xml
      - uses: codecov/codecov-action@v3
```

## Troubleshooting

### ImportError: No module named 'app'
Make sure you're running pytest from the project root directory.

### Database locked errors
Use separate test database (handled automatically by fixtures).

### Slow tests
Run only fast tests: `pytest -m "not slow"`
