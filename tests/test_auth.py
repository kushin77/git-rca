"""
Unit tests for authentication and authorization middleware.

Tests:
- Token generation and validation
- Bearer token extraction
- Role-based access control (RBAC)
- Token expiration
- Invalid token handling
"""

import json
import hashlib
import base64
import pytest
from datetime import datetime, timedelta, UTC

from src.middleware.auth import (
    TokenValidator,
    extract_bearer_token,
    AuthError,
    require_auth,
)


class TestTokenValidator:
    """Tests for TokenValidator class."""
    
    @pytest.fixture
    def validator(self):
        """Create token validator for tests."""
        return TokenValidator(secret_key='test_secret')
    
    def test_generate_token_valid(self, validator):
        """Test generating a valid token."""
        token = validator.generate_token('user123', 'engineer')
        assert token is not None
        assert '.' in token  # Should have payload.signature format
    
    def test_generate_token_invalid_role(self, validator):
        """Test generating token with invalid role raises error."""
        with pytest.raises(ValueError):
            validator.generate_token('user123', 'superuser')
    
    def test_validate_token_success(self, validator):
        """Test validating a valid token."""
        token = validator.generate_token('user123', 'engineer')
        payload = validator.validate_token(token)
        
        assert payload['user_id'] == 'user123'
        assert payload['role'] == 'engineer'
        assert 'iat' in payload
        assert 'exp' in payload
    
    def test_validate_token_missing(self, validator):
        """Test validating with no token raises error."""
        with pytest.raises(AuthError) as exc:
            validator.validate_token('')
        assert 'Token required' in str(exc.value)
    
    def test_validate_token_invalid_format(self, validator):
        """Test validating token with invalid format."""
        with pytest.raises(AuthError) as exc:
            validator.validate_token('invalid_token_no_signature')
        assert 'Invalid token format' in str(exc.value)
    
    def test_validate_token_tampered_signature(self, validator):
        """Test validating token with tampered signature."""
        token = validator.generate_token('user123', 'engineer')
        # Tamper with the token
        parts = token.split('.')
        tampered = f"{parts[0]}.badbadbad"
        
        with pytest.raises(AuthError) as exc:
            validator.validate_token(tampered)
        assert 'Invalid token signature' in str(exc.value)
    
    def test_token_expires(self, validator):
        """Test that expired tokens are rejected."""
        # Create token that expires in the past (-1 hour)
        import base64
        
        now = datetime.now(UTC)
        expired_exp = int((now - timedelta(hours=1)).timestamp())
        
        # Manually create an expired token
        payload = {
            'user_id': 'user123',
            'role': 'engineer',
            'iat': int(now.timestamp()),
            'exp': expired_exp,
        }
        
        payload_str = json.dumps(payload, sort_keys=True)
        payload_b64 = base64.urlsafe_b64encode(payload_str.encode()).decode().rstrip('=')
        signature = hashlib.sha256(
            (payload_str + validator.secret_key).encode()
        ).hexdigest()[:16]
        token = f"{payload_b64}.{signature}"
        
        # Token should be rejected as expired
        with pytest.raises(AuthError) as exc:
            validator.validate_token(token)
        assert 'Token expired' in str(exc.value)


class TestBearerTokenExtraction:
    """Tests for Bearer token extraction from headers."""
    
    def test_extract_valid_bearer_token(self):
        """Test extracting valid Bearer token."""
        auth_header = "Bearer my_token_value"
        token = extract_bearer_token(auth_header)
        assert token == "my_token_value"
    
    def test_extract_no_bearer_token(self):
        """Test extracting from header without Bearer."""
        auth_header = "Basic base64encodedcreds"
        token = extract_bearer_token(auth_header)
        assert token is None
    
    def test_extract_no_auth_header(self):
        """Test extracting from missing auth header."""
        token = extract_bearer_token(None)
        assert token is None
    
    def test_extract_malformed_header(self):
        """Test extracting from malformed Bearer header."""
        auth_header = "Bearer"  # Missing token
        token = extract_bearer_token(auth_header)
        assert token is None
    
    def test_extract_case_insensitive(self):
        """Test Bearer keyword is case-insensitive."""
        auth_header = "bearer my_token_value"
        token = extract_bearer_token(auth_header)
        assert token == "my_token_value"


class TestAuthDecorator:
    """Tests for @require_auth decorator with Flask app."""
    
    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        from flask import Flask
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test_secret_key_for_auth_tests'
        
        from src.middleware import init_auth
        init_auth(app)
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    @pytest.fixture
    def app_with_routes(self, app):
        """Add test routes to app."""
        from src.middleware import require_auth
        
        @app.get('/api/public')
        def public_endpoint():
            """Public endpoint (no auth required)."""
            return {'message': 'public'}, 200
        
        @app.get('/api/protected')
        @require_auth()
        def protected_endpoint():
            """Protected endpoint (any authenticated user)."""
            return {
                'message': 'protected',
                'user_id': request.user_id,
                'role': request.user_role,
            }, 200
        
        @app.post('/api/admin')
        @require_auth(allowed_roles={'admin'})
        def admin_endpoint():
            """Admin-only endpoint."""
            return {'message': 'admin', 'user_id': request.user_id}, 200
        
        from flask import request
        return app
    
    def test_public_endpoint_no_auth(self, client, app_with_routes):
        """Test public endpoint doesn't require auth."""
        response = client.get('/api/public')
        assert response.status_code == 200
    
    def test_protected_endpoint_no_token(self, client, app_with_routes):
        """Test protected endpoint requires token."""
        response = client.get('/api/protected')
        assert response.status_code == 401
        data = response.get_json()
        assert 'Unauthorized' in data['error']
    
    def test_protected_endpoint_valid_token(self, client, app_with_routes):
        """Test protected endpoint with valid token."""
        # Generate token
        with app_with_routes.app_context():
            from src.middleware import get_token_validator
            validator = get_token_validator()
            token = validator.generate_token('user123', 'engineer')
        
        # Use token
        response = client.get(
            '/api/protected',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['user_id'] == 'user123'
        assert data['role'] == 'engineer'
    
    def test_protected_endpoint_invalid_token(self, client, app_with_routes):
        """Test protected endpoint with invalid token."""
        response = client.get(
            '/api/protected',
            headers={'Authorization': 'Bearer invalid_token'}
        )
        assert response.status_code == 401
    
    def test_admin_endpoint_insufficient_role(self, client, app_with_routes):
        """Test admin endpoint rejects non-admin users."""
        with app_with_routes.app_context():
            from src.middleware import get_token_validator
            validator = get_token_validator()
            token = validator.generate_token('user123', 'engineer')
        
        response = client.post(
            '/api/admin',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 403
        data = response.get_json()
        assert 'Forbidden' in data['error']
    
    def test_admin_endpoint_with_admin_token(self, client, app_with_routes):
        """Test admin endpoint with admin token."""
        with app_with_routes.app_context():
            from src.middleware import get_token_validator
            validator = get_token_validator()
            token = validator.generate_token('admin_user', 'admin')
        
        response = client.post(
            '/api/admin',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['user_id'] == 'admin_user'


class TestAuthDebugEndpoint:
    """Tests for /auth/token debug endpoint."""
    
    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        from flask import Flask
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['ENV'] = 'development'
        
        from src.middleware import init_auth
        init_auth(app)
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    def test_get_token_default(self, client):
        """Test getting a token with defaults."""
        response = client.post('/auth/token', json={})
        assert response.status_code == 200
        data = response.get_json()
        assert 'token' in data
        assert data['user_id'] == 'test_user'
        assert data['role'] == 'engineer'
    
    def test_get_token_custom_user(self, client):
        """Test getting token with custom user_id."""
        response = client.post(
            '/auth/token',
            json={'user_id': 'alice', 'role': 'admin'}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['user_id'] == 'alice'
        assert data['role'] == 'admin'
    
    def test_get_token_invalid_role(self, client):
        """Test getting token with invalid role."""
        response = client.post(
            '/auth/token',
            json={'user_id': 'bob', 'role': 'hacker'}
        )
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
