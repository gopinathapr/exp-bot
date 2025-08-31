# Testing Documentation for Expense Bot

## Overview

This document provides comprehensive information about the testing strategy and implementation for the Expense Bot application.

## Test Structure

The testing suite is organized into two main categories:

### 1. Unit Tests (`test_bot.py`)
- **Configuration Tests**: Test the `Config` class initialization and validation
- **Model Tests**: Test the `ExpenseItem` class and its methods
- **Utility Function Tests**: Test helper functions like `ist_date()`, `match_keywords()`, etc.
- **Type Detection Tests**: Test expense categorization functionality
- **Google Sheets Integration Tests**: Test API interactions (mocked)
- **Async Function Tests**: Test asynchronous operations
- **API Endpoint Tests**: Test FastAPI endpoints
- **Authorization Tests**: Test the `@restricted` decorator

### 2. Integration Tests (`test_integration.py`)
- **Workflow Tests**: Test complete user workflows end-to-end
- **Component Integration**: Test how different components work together
- **Error Handling**: Test error scenarios across components
- **Data Validation**: Test data flow and validation across the system

## Test Coverage Areas

### Core Functionality
- ✅ Expense logging and processing
- ✅ Type detection and categorization
- ✅ Reminder system
- ✅ Credit card payment reminders
- ✅ Expense summaries and reports
- ✅ Google Sheets integration
- ✅ User authorization and security

### API Endpoints
- ✅ `/types_refresh` - Types data refresh
- ✅ `/reminders` - Reminder processing
- ✅ `/bot` - Telegram webhook processing
- ✅ Authentication and authorization

### Data Models
- ✅ `ExpenseItem` class functionality
- ✅ Data validation and type conversion
- ✅ Error handling for invalid data

### Configuration Management
- ✅ Environment variable loading
- ✅ Local vs production settings
- ✅ User configuration
- ✅ Google Sheets configuration

## Running Tests

### Prerequisites

1. Install test dependencies:
```bash
pip install -r requirements-test.txt
```

### Quick Start

Run all tests with coverage:
```bash
python run_tests.py
```

### Test Runner Options

```bash
# Run only unit tests
python run_tests.py --type unit

# Run only integration tests
python run_tests.py --type integration

# Run without coverage report
python run_tests.py --no-coverage

# Install dependencies and run tests
python run_tests.py --install-deps

# Run in quiet mode
python run_tests.py --quiet
```

### Manual pytest Execution

```bash
# Run all tests with coverage
pytest test_bot.py test_integration.py --cov=bot --cov-report=html

# Run specific test file
pytest test_bot.py -v

# Run specific test class
pytest test_bot.py::TestConfig -v

# Run specific test method
pytest test_bot.py::TestConfig::test_config_initialization_with_required_env -v
```

## Test Configuration

### Pytest Configuration (`pytest.ini`)
- Test discovery patterns
- Coverage settings (minimum 80% coverage)
- Output formatting
- Async test support

### Coverage Configuration
- HTML reports generated in `htmlcov/`
- Terminal coverage summary
- Minimum coverage threshold: 70%

## Mocking Strategy

### External Dependencies
- **Google Sheets API**: Mocked using `unittest.mock`
- **Telegram Bot API**: Mocked for message handling
- **File System**: Mocked for configuration and data files
- **Environment Variables**: Patched for different test scenarios

### Key Mocking Patterns
```python
# Mocking Google Sheets API
@patch('bot.build')
@patch('bot.get_creds')
def test_function(mock_get_creds, mock_build):
    # Test implementation

# Mocking async functions
@patch('bot.bot_builder.bot.send_message', new_callable=AsyncMock)
async def test_async_function(mock_send):
    # Test implementation

# Mocking file operations
@patch('bot.open', mock_open(read_data='test data'))
def test_file_function():
    # Test implementation
```

## Test Data Management

### Mock Data Patterns
- **Expense Data**: Standardized `ExpenseItem` objects for testing
- **Configuration**: Environment variable combinations for different scenarios
- **API Responses**: Standard Google Sheets API response formats
- **User Data**: Mock Telegram user and message objects

### Test Fixtures
```python
# Sample expense data
expenses = [
    ExpenseItem(1, "24/07", "Coffee", "150", "Food", "Beverages"),
    ExpenseItem(2, "24/07", "Lunch", "300", "Food", "Meals")
]

# Sample reminder data
reminders = [
    {"desc": "Rent", "date_range": "1-5", "main_type": "Housing", "sub_type": "Rent"}
]
```

## Error Testing Strategy

### Error Scenarios Covered
1. **API Failures**: Google Sheets API errors, network issues
2. **File System Errors**: Missing files, permission issues, JSON parsing errors
3. **Data Validation Errors**: Invalid expense amounts, malformed dates
4. **Authentication Errors**: Invalid tokens, unauthorized users
5. **Configuration Errors**: Missing environment variables

### Error Handling Validation
- Graceful error recovery
- Appropriate error messages
- Logging verification
- User-friendly error responses

## Continuous Integration

### Test Automation
Tests are designed to be run in CI/CD pipelines with:
- Environment variable configuration
- Dependency installation
- Coverage reporting
- Test result artifacts

### CI Configuration Example
```yaml
# Example GitHub Actions workflow
- name: Run Tests
  run: |
    pip install -r requirements-test.txt
    python run_tests.py --type all
    
- name: Upload Coverage
  uses: codecov/codecov-action@v1
  with:
    file: ./coverage.xml
```

## Performance Testing

### Async Function Testing
- Proper async/await usage validation
- Mock async operations
- Event loop management in tests

### Test Execution Speed
- Mocked external API calls for fast execution
- Isolated test cases to prevent interference
- Parallel test execution support

## Debugging Tests

### Common Issues and Solutions

1. **Import Errors**: Ensure all dependencies are installed
2. **Async Test Failures**: Use `unittest.IsolatedAsyncioTestCase` for async tests
3. **Mock Not Working**: Verify patch paths and object references
4. **Coverage Issues**: Check file paths and import statements

### Debugging Commands
```bash
# Run with debugging output
pytest -v -s test_bot.py::TestConfig::test_config_initialization

# Run with print statements (disable capture)
pytest -v -s --capture=no

# Run with coverage debugging
pytest --cov=bot --cov-report=term-missing -v
```

## Test Maintenance

### Regular Tasks
1. **Update test data** when business logic changes
2. **Review coverage reports** and add tests for uncovered code
3. **Update mocks** when external APIs change
4. **Refactor tests** when code structure changes

### Best Practices
- Keep tests simple and focused
- Use descriptive test names
- Mock external dependencies consistently
- Maintain test data fixtures
- Document complex test scenarios

## Test Metrics

### Current Coverage
- Target: 80% minimum coverage
- Critical functions: 95%+ coverage
- Integration paths: Full coverage

### Test Counts
- Unit tests: ~25 test methods
- Integration tests: ~10 test methods
- API tests: ~5 test methods
- Error handling tests: ~8 test methods

## Future Enhancements

### Planned Improvements
1. **Load Testing**: Performance testing for high-volume scenarios
2. **Security Testing**: Penetration testing for API endpoints
3. **End-to-End Testing**: Full workflow testing with real APIs (in staging)
4. **Property-Based Testing**: Using hypothesis for edge case discovery

### Test Environment Improvements
1. **Test Database**: Separate test data storage
2. **Test Isolation**: Better isolation between test runs
3. **Parallel Testing**: Improved parallel test execution
4. **Test Reporting**: Enhanced test result reporting and analytics
