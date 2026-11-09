import os
import pytest
from unittest.mock import patch, MagicMock

# Set test environment variables before importing app modules
os.environ["FLASK_ENV"] = "testing"
os.environ["FLASK_SECRET_KEY"] = "test-secret-key-for-testing"
os.environ["GOOGLE_CLIENT_ID"] = "test-google-client-id.apps.googleusercontent.com"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:3000,https://turiya-portfolio-platform.vercel.app"

from api.index import create_app
from api.finance.utils import stock_info_cache, index_quote_cache


@pytest.fixture
def app():
    """Create Flask application instance in testing mode."""
    application = create_app({"TESTING": True})
    return application


@pytest.fixture
def client(app):
    """Test client fixture."""
    return app.test_client()


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear memory caches between tests to avoid cross-test pollution."""
    stock_info_cache.clear()
    index_quote_cache.clear()
    yield
    stock_info_cache.clear()
    index_quote_cache.clear()


@pytest.fixture
def mock_google_user():
    """Mock verified Google user record."""
    return {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "email": "testuser@example.com",
        "role": "client",
        "name": "Test User",
        "verified": True,
        "created_at": "2025-01-01T00:00:00Z",
    }


@pytest.fixture
def authenticated_client(app, mock_google_user):
    """
    Test client that simulates an authenticated user by mocking Google token verification
    and user database retrieval in google_jwt_required decorator.
    """
    with patch("api.auth.auth.id_token.verify_oauth2_token") as mock_verify, \
         patch("api.auth.auth.db_query") as mock_db:
        
        mock_verify.return_value = {
            "iss": "https://accounts.google.com",
            "email": mock_google_user["email"],
            "name": mock_google_user["name"],
        }
        mock_db.return_value = mock_google_user

        client = app.test_client()
        yield client

