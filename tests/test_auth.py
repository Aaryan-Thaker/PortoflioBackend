import os
import pytest
from unittest.mock import patch, MagicMock
from api.index import create_app


def test_health_check_ping(client):
    """Test the base health check endpoint."""
    response = client.get("/api/ping")
    assert response.status_code == 200
    assert response.is_json
    data = response.get_json()
    assert data == {"ping": "pong"}


def test_production_secret_key_required():
    """Verify ValueError is raised if FLASK_SECRET_KEY is missing in production."""
    with patch.dict(os.environ, {"FLASK_ENV": "production"}, clear=False):
        os.environ.pop("FLASK_SECRET_KEY", None)
        with pytest.raises(ValueError, match="FLASK_SECRET_KEY environment variable must be set in production"):
            create_app()


def test_production_secret_key_accepted():
    """Verify production starts successfully when FLASK_SECRET_KEY is provided."""
    with patch.dict(os.environ, {"FLASK_ENV": "production", "FLASK_SECRET_KEY": "secure_prod_key_123"}, clear=False):
        prod_app = create_app()
        assert prod_app.secret_key == "secure_prod_key_123"


def test_development_fallback_secret_key():
    """Verify development uses fallback secret key with a warning."""
    with patch.dict(os.environ, {"FLASK_ENV": "development"}, clear=False):
        os.environ.pop("FLASK_SECRET_KEY", None)
        dev_app = create_app()
        assert dev_app.secret_key == "dev_secret_key_change_in_production"


def test_cors_allowed_origins(client):
    """Verify CORS headers are returned for configured origins with credentials: true."""
    # Test localhost:3000
    res_local = client.get("/api/ping", headers={"Origin": "http://localhost:3000"})
    assert res_local.status_code == 200
    assert res_local.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"
    assert res_local.headers.get("Access-Control-Allow-Credentials") == "true"

    # Test production Vercel app
    res_prod = client.get("/api/ping", headers={"Origin": "https://turiya-portfolio-platform.vercel.app"})
    assert res_prod.status_code == 200
    assert res_prod.headers.get("Access-Control-Allow-Origin") == "https://turiya-portfolio-platform.vercel.app"
    assert res_prod.headers.get("Access-Control-Allow-Credentials") == "true"


def test_cors_rejects_unauthorized_origin(client):
    """Verify unauthorized origins do not receive Access-Control-Allow-Origin."""
    res = client.get("/api/ping", headers={"Origin": "https://malicious-site.com"})
    assert res.status_code == 200
    assert "Access-Control-Allow-Origin" not in res.headers


def test_cors_options_preflight(client):
    """Verify OPTIONS preflight request succeeds and returns CORS headers."""
    res = client.options(
        "/api/oauth/login",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type,Authorization",
        },
    )
    assert res.status_code == 200
    assert res.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"
    assert res.headers.get("Access-Control-Allow-Credentials") == "true"


def test_jwt_required_missing_header(client):
    """Verify protected routes reject requests without Authorization header."""
    res = client.post("/api/oauth/login", json={})
    assert res.status_code == 401
    assert "Authorization header missing or invalid" in res.get_json().get("message", "")


def test_jwt_required_invalid_format(client):
    """Verify protected routes reject requests with invalid Authorization format."""
    res = client.post("/api/oauth/login", headers={"Authorization": "Basic invalid123"})
    assert res.status_code == 401
    assert "Authorization header missing or invalid" in res.get_json().get("message", "")


def test_oauth_login_success(app, mock_google_user):
    """Verify successful Google OAuth login returns user record without wildcard CORS."""
    with patch("api.auth.auth.id_token.verify_oauth2_token") as mock_verify, \
         patch("api.auth.auth.db_query") as mock_db, \
         patch("api.auth.routes.db_query") as mock_routes_db:

        mock_verify.return_value = {
            "iss": "https://accounts.google.com",
            "email": mock_google_user["email"],
            "name": mock_google_user["name"],
        }
        mock_db.return_value = mock_google_user
        mock_routes_db.return_value = mock_google_user

        client = app.test_client()
        res = client.post(
            "/api/oauth/login",
            headers={
                "Authorization": "Bearer mock-google-token-123",
                "Origin": "http://localhost:3000",
            },
        )

        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert data["user"]["email"] == mock_google_user["email"]
        # Verify no wildcard origin
        assert res.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"
        assert res.headers.get("Access-Control-Allow-Origin") != "*"

