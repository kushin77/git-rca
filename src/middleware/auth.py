"""
Authentication and authorization middleware for Investigation RCA Platform.

Provides:
- Bearer token validation (JWT-compatible)
- Role-based access control (RBAC)
- Decorators for protecting endpoints
- Token generation/validation for testing
"""

import functools
import hashlib
import json
import os
import base64
from datetime import datetime, timedelta, UTC
from typing import Dict, Optional, Set

from flask import current_app, request, jsonify


class AuthError(Exception):
    """Raised when authentication fails."""
    pass


class TokenValidator:
    """Validates and manages JWT-like tokens for MVP."""
    
    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize token validator.
        
        Args:
            secret_key: Secret key for token signing. If None, uses env var
                       or generates a test key.
        """
        self.secret_key = secret_key or os.getenv(
            'JWT_SECRET',
            'dev_secret_key_change_in_production'
        )
        
        # In-memory token whitelist for MVP (replace with DB in Phase 2)
        self.valid_tokens: Dict[str, dict] = {}
    
    def generate_token(
        self,
        user_id: str,
        role: str = 'engineer',
        expires_in_hours: int = 24
    ) -> str:
        """
        Generate a test token for development/testing.
        
        Args:
            user_id: Unique user identifier
            role: User role (admin, engineer, viewer)
            expires_in_hours: Token expiration time in hours
            
        Returns:
            Token string (simple format: base64_payload|signature)
        """
        if role not in ('admin', 'engineer', 'viewer'):
            raise ValueError(f"Invalid role: {role}")
        
        now = datetime.now(UTC)
        expiry = now + timedelta(hours=expires_in_hours)
        
        # Create token payload using timestamps instead of ISO format
        # to avoid dots in the payload (which break token parsing)
        payload = {
            'user_id': user_id,
            'role': role,
            'iat': int(now.timestamp()),
            'exp': int(expiry.timestamp()),
        }
        
        # Base64-encode payload to avoid spaces in token
        payload_str = json.dumps(payload, sort_keys=True)
        payload_b64 = base64.urlsafe_b64encode(payload_str.encode()).decode().rstrip('=')
        
        # Simple signature (in production, use proper JWT library)
        signature = hashlib.sha256(
            (payload_str + self.secret_key).encode()
        ).hexdigest()[:16]
        
        token = f"{payload_b64}.{signature}"
        
        # Store in whitelist for validation (use original payload_str as key)
        self.valid_tokens[token] = payload
        
        return token
    
    def validate_token(self, token: str) -> Dict:
        """
        Validate a token and return its payload.
        
        Args:
            token: Bearer token to validate
            
        Returns:
            Token payload dict with user_id, role, iat, exp
            
        Raises:
            AuthError: If token is invalid or expired
        """
        if not token:
            raise AuthError("Token required")
        
        try:
            # Split token and signature using dot separator
            parts = token.split('.')
            if len(parts) != 2:
                raise AuthError("Invalid token format")
            
            payload_b64, signature = parts
            
            # Decode base64 payload (add padding if needed)
            padding = 4 - (len(payload_b64) % 4)
            if padding != 4:
                payload_b64 += '=' * padding
            
            payload_str = base64.urlsafe_b64decode(payload_b64).decode()
            payload = json.loads(payload_str)
            
            # Verify signature
            expected_sig = hashlib.sha256(
                (payload_str + self.secret_key).encode()
            ).hexdigest()[:16]
            
            if signature != expected_sig:
                raise AuthError("Invalid token signature")
            
            # Check expiration (using timestamp comparison)
            exp_timestamp = payload.get('exp')
            if not isinstance(exp_timestamp, int):
                raise AuthError("Invalid expiration time")
            
            current_timestamp = int(datetime.now(UTC).timestamp())
            if current_timestamp > exp_timestamp:
                raise AuthError("Token expired")
            
            return payload
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise AuthError(f"Invalid token: {str(e)}")


# Global token validator instance
_token_validator: Optional[TokenValidator] = None


def get_token_validator() -> TokenValidator:
    """Get or create the global token validator."""
    global _token_validator
    if _token_validator is None:
        _token_validator = TokenValidator()
    return _token_validator


def extract_bearer_token(authorization_header: Optional[str]) -> Optional[str]:
    """
    Extract Bearer token from Authorization header.
    
    Args:
        authorization_header: Authorization header value
        
    Returns:
        Token string or None if not present/invalid
    """
    if not authorization_header:
        return None
    
    parts = authorization_header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    
    return parts[1]


def require_auth(allowed_roles: Optional[Set[str]] = None):
    """
    Decorator to protect endpoints with authentication.
    
    Args:
        allowed_roles: Set of roles allowed to access endpoint.
                      If None, all authenticated users allowed.
    
    Usage:
        @app.post('/api/investigations')
        @require_auth(allowed_roles={'admin', 'engineer'})
        def create_investigation():
            user_id = request.user_id
            role = request.user_role
            ...
    """
    if allowed_roles is None:
        allowed_roles = {'admin', 'engineer', 'viewer'}
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Extract Bearer token
            auth_header = request.headers.get('Authorization')
            token = extract_bearer_token(auth_header)
            
            if not token:
                return jsonify({
                    'error': 'Unauthorized',
                    'message': 'Missing or invalid Authorization header'
                }), 401
            
            try:
                # Validate token
                validator = get_token_validator()
                payload = validator.validate_token(token)
                
                # Check role
                user_role = payload.get('role')
                if user_role not in allowed_roles:
                    return jsonify({
                        'error': 'Forbidden',
                        'message': f'Role {user_role} not allowed for this endpoint'
                    }), 403
                
                # Attach user info to request context
                request.user_id = payload.get('user_id')
                request.user_role = user_role
                request.token_payload = payload
                
            except AuthError as e:
                return jsonify({
                    'error': 'Unauthorized',
                    'message': str(e)
                }), 401
            
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def init_auth(app):
    """
    Initialize authentication module with Flask app.
    
    Usage:
        app = create_app()
        init_auth(app)
    """
    # Set up global token validator with app's secret
    global _token_validator
    secret_key = app.config.get('SECRET_KEY', os.getenv('JWT_SECRET'))
    _token_validator = TokenValidator(secret_key=secret_key)
    
    # Add auth debug endpoint (remove in production)
    @app.post('/auth/token')
    def get_token():
        """Debug endpoint to generate test tokens."""
        if app.config.get('ENV') == 'production':
            return jsonify({'error': 'Not available in production'}), 403
        
        data = request.get_json() or {}
        user_id = data.get('user_id', 'test_user')
        role = data.get('role', 'engineer')
        
        try:
            validator = get_token_validator()
            token = validator.generate_token(user_id, role)
            return jsonify({
                'token': token,
                'user_id': user_id,
                'role': role,
                'message': 'Token valid for 24 hours'
            }), 200
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
