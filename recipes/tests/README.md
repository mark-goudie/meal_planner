# Test Suite for Meal Planner Application

This directory contains a comprehensive test suite for the meal planner Django application.

## Test Structure

The tests are organized into separate modules for better maintainability:

### Core Test Files

- **`test_models.py`** - Tests for all Django models (Recipe, Tag, MealPlan, FamilyPreference)
- **`test_views.py`** - Tests for all view functions including authentication and permissions  
- **`test_forms.py`** - Tests for form validation and functionality
- **`test_urls.py`** - Tests for URL routing and resolution
- **`test_templatetags.py`** - Tests for custom template tags and filters
- **`test_integration.py`** - End-to-end integration tests for complete workflows
- **`test_utils.py`** - Utility functions and helper classes for testing

### Test Coverage

#### Models (test_models.py)
- ✅ Recipe model creation, relationships, and validation
- ✅ Tag model uniqueness constraints
- ✅ MealPlan model with date defaults and choices
- ✅ FamilyPreference model with unique constraints
- ✅ All model string representations and relationships

#### Views (test_views.py)
- ✅ Public views (register, privacy, terms, disclaimer)
- ✅ Recipe CRUD operations with user isolation
- ✅ AI recipe generation (mocked)
- ✅ Meal planning functionality
- ✅ Family preference management
- ✅ Shopping list generation
- ✅ Authentication and authorization
- ✅ Filtering and search functionality

#### Forms (test_forms.py)
- ✅ RecipeForm validation and saving
- ✅ MealPlanForm with user-specific recipe filtering
- ✅ FamilyPreferenceForm validation
- ✅ CustomUserCreationForm with email requirement
- ✅ Form widget attributes and help texts
- ✅ Integration between forms

#### URLs (test_urls.py)
- ✅ All URL patterns resolve correctly
- ✅ URL names are consistent and accessible
- ✅ Protected URLs require authentication
- ✅ Public URLs are accessible without login

#### Template Tags (test_templatetags.py)
- ✅ get_meal filter for meal plan retrieval
- ✅ get filter for dictionary access
- ✅ ai_generate_surprise_recipe function (mocked)
- ✅ Template tag integration scenarios

#### Integration Tests (test_integration.py)
- ✅ Complete recipe workflow (create → meal plan → preferences → favorites)
- ✅ Weekly meal planning workflow
- ✅ Search and filtering combinations
- ✅ Shopping list generation and deduplication
- ✅ User data isolation and security

## Running Tests

### Prerequisites

Make sure you have the required packages installed:
```bash
pip install -r requirements.txt
```

### Run All Tests

```bash
# Using Django's test runner
python manage.py test

# Using pytest (if installed)
pytest
```

### Run Specific Test Modules

```bash
# Run only model tests
python manage.py test recipes.tests.test_models

# Run only view tests  
python manage.py test recipes.tests.test_views

# Run integration tests
python manage.py test recipes.tests.test_integration
```

### Run Tests with Coverage

```bash
# Install coverage first
pip install coverage

# Run tests with coverage
coverage run --source='.' manage.py test
coverage report
coverage html  # Generates HTML coverage report
```

### Run Tests by Category

Using pytest markers (if pytest is installed):

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Skip AI-related tests (useful when no API key)
pytest -m "not ai"
```

## Test Configuration

### Settings
- Tests use a separate SQLite database created automatically by Django
- AI-related tests are mocked to avoid requiring actual OpenAI API calls
- Test database is cleaned up automatically after each test

### Environment Variables
For tests that require environment variables:
- `OPENAI_API_KEY` - Not required for tests (mocked)
- `SECRET_KEY` - Uses Django's test settings default

### Test Data
- Test utilities in `test_utils.py` provide helper functions for creating test data
- Each test class sets up its own isolated test data
- No test data persists between test runs

## Best Practices

### When Adding New Tests

1. **Model Tests**: Add tests to `test_models.py` for new model fields, methods, or relationships
2. **View Tests**: Add tests to `test_views.py` for new views, ensuring both positive and negative cases
3. **Form Tests**: Add tests to `test_forms.py` for new forms or form validation
4. **Integration Tests**: Add end-to-end tests to `test_integration.py` for new workflows

### Test Data Creation

Use the utilities in `test_utils.py`:

```python
from recipes.tests.test_utils import TestUtilities

# Create a complete test environment
test_data = TestUtilities.create_complete_test_data()
user = test_data['user']
recipes = test_data['recipes']

# Or create specific objects
user = TestUtilities.create_test_user()
recipe = TestUtilities.create_test_recipe(user)
```

### Mocking External Services

AI/OpenAI calls are mocked in tests:

```python
@patch('recipes.views.openai.OpenAI')
def test_ai_functionality(self, mock_openai):
    # Mock the response
    mock_client = Mock()
    mock_openai.return_value = mock_client
    # ... set up mock response
```

## Current Test Stats

- **Total Tests**: 100+ comprehensive tests
- **Model Coverage**: Complete coverage of all models
- **View Coverage**: All views tested including edge cases
- **Integration Coverage**: Major workflows tested end-to-end
- **Security Coverage**: Authentication and user isolation tested

## Troubleshooting

### Common Issues

1. **Database Errors**: Ensure migrations are up to date
   ```bash
   python manage.py migrate
   ```

2. **Import Errors**: Make sure you're in the project root directory

3. **Mock Errors**: AI-related tests use mocks - ensure `unittest.mock` is available

4. **Permission Errors**: Some tests check user permissions - ensure test users are set up correctly

### Running Specific Failing Tests

```bash
# Run a specific test method
python manage.py test recipes.tests.test_models.RecipeModelTest.test_create_recipe_minimal

# Run with verbose output for debugging
python manage.py test --verbosity=2
```

## Future Enhancements

Potential areas for additional testing:
- Performance testing for large datasets
- Frontend/JavaScript testing
- Load testing for concurrent users
- Testing with PostgreSQL database
- API endpoint testing (if added)
- Email functionality testing (if added)