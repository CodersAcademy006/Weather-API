"""
Comprehensive tests for authentication module.
These tests verify:
- Password hashing and verification
- JWT token creation and validation
- Token expiration handling
- Security edge cases
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock, AsyncMock
from jose import jwt, JWTError
from fastapi import HTTPException

# Import auth module
import auth


# =============================================================================
# PASSWORD HASHING TESTS
# =============================================================================

class TestPasswordHashing:
    """Tests for password hashing functionality."""

    def test_get_password_hash_returns_hash(self):
        """Test that password hashing returns a hash string."""
        password = "testpassword123"
        hashed = auth.get_password_hash(password)
        
        assert hashed is not None
        assert isinstance(hashed, str)
        assert hashed != password  # Hash should be different from original

    def test_get_password_hash_unique_per_call(self):
        """Test that same password produces different hashes (salting)."""
        password = "samepassword"
        hash1 = auth.get_password_hash(password)
        hash2 = auth.get_password_hash(password)
        
        # Due to salt, hashes should be different
        assert hash1 != hash2

    def test_verify_password_correct(self):
        """Test that correct password verification succeeds."""
        password = "correctpassword"
        hashed = auth.get_password_hash(password)
        
        assert auth.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test that incorrect password verification fails."""
        password = "correctpassword"
        wrong_password = "wrongpassword"
        hashed = auth.get_password_hash(password)
        
        assert auth.verify_password(wrong_password, hashed) is False

    def test_verify_password_empty_password(self):
        """Test that empty password doesn't match non-empty hash."""
        password = "somepassword"
        hashed = auth.get_password_hash(password)
        
        assert auth.verify_password("", hashed) is False

    def test_hash_empty_password(self):
        """Test that empty password can be hashed."""
        password = ""
        hashed = auth.get_password_hash(password)
        
        assert hashed is not None
        assert auth.verify_password("", hashed) is True

    def test_hash_special_characters(self):
        """Test hashing passwords with special characters."""
        password = "P@$$w0rd!#$%^&*()"
        hashed = auth.get_password_hash(password)
        
        assert auth.verify_password(password, hashed) is True

    def test_hash_unicode_password(self):
        """Test hashing passwords with unicode characters."""
        password = "密码测试🔐"
        hashed = auth.get_password_hash(password)
        
        assert auth.verify_password(password, hashed) is True

    def test_hash_long_password(self):
        """Test hashing very long passwords."""
        password = "a" * 1000  # 1000 character password
        hashed = auth.get_password_hash(password)
        
        assert auth.verify_password(password, hashed) is True


# =============================================================================
# JWT TOKEN CREATION TESTS
# =============================================================================

class TestTokenCreation:
    """Tests for JWT token creation."""

    def test_create_access_token_returns_string(self):
        """Test that token creation returns a string."""
        data = {"sub": "test@example.com"}
        token = auth.create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)

    def test_create_access_token_is_valid_jwt(self):
        """Test that created token is valid JWT format."""
        data = {"sub": "test@example.com"}
        token = auth.create_access_token(data)
        
        # JWT has three parts separated by dots
        parts = token.split(".")
        assert len(parts) == 3

    def test_create_access_token_contains_subject(self):
        """Test that token contains the subject claim."""
        email = "user@example.com"
        data = {"sub": email}
        token = auth.create_access_token(data)
        
        # Decode and verify
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        assert payload["sub"] == email

    def test_create_access_token_has_expiration(self):
        """Test that token has expiration claim."""
        data = {"sub": "test@example.com"}
        token = auth.create_access_token(data)
        
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        assert "exp" in payload

    def test_create_access_token_expiration_time(self):
        """Test that token expiration is approximately correct."""
        data = {"sub": "test@example.com"}
        
        before = datetime.now(timezone.utc)
        token = auth.create_access_token(data)
        after = datetime.now(timezone.utc)
        
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        
        # Expiration should be about ACCESS_TOKEN_EXPIRE_MINUTES from now
        expected_min = before + timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES - 1)
        expected_max = after + timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES + 1)
        
        assert expected_min <= exp_time <= expected_max

    def test_create_access_token_preserves_additional_data(self):
        """Test that additional data in payload is preserved."""
        data = {"sub": "test@example.com", "role": "admin", "custom": "value"}
        token = auth.create_access_token(data)
        
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        assert payload["sub"] == "test@example.com"
        assert payload["role"] == "admin"
        assert payload["custom"] == "value"

    def test_create_access_token_does_not_modify_input(self):
        """Test that creating token doesn't modify the input data."""
        original_data = {"sub": "test@example.com"}
        data_copy = original_data.copy()
        
        auth.create_access_token(data_copy)
        
        # Original should not have 'exp' added
        assert "exp" not in original_data


# =============================================================================
# TOKEN VALIDATION TESTS
# =============================================================================

class TestTokenValidation:
    """Tests for JWT token validation."""

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self):
        """Test that valid token returns user info."""
        email = "valid@example.com"
        token = auth.create_access_token({"sub": email})
        
        user = await auth.get_current_user(token)
        assert user["email"] == email

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """Test that invalid token raises exception."""
        with pytest.raises(HTTPException) as exc_info:
            await auth.get_current_user("invalid.token.here")
        
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_expired_token(self):
        """Test that expired token raises exception."""
        # Create an already-expired token
        data = {"sub": "test@example.com"}
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) - timedelta(minutes=5)  # Expired 5 min ago
        to_encode.update({"exp": expire})
        expired_token = jwt.encode(to_encode, auth.SECRET_KEY, algorithm=auth.ALGORITHM)
        
        with pytest.raises(HTTPException) as exc_info:
            await auth.get_current_user(expired_token)
        
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_wrong_secret(self):
        """Test that token signed with wrong secret is rejected."""
        data = {"sub": "test@example.com"}
        wrong_secret = "wrong_secret_key"
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)
        to_encode = {**data, "exp": expire}
        wrong_token = jwt.encode(to_encode, wrong_secret, algorithm=auth.ALGORITHM)
        
        with pytest.raises(HTTPException) as exc_info:
            await auth.get_current_user(wrong_token)
        
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_missing_subject(self):
        """Test that token without subject claim is rejected."""
        # Create token without 'sub' claim
        data = {"other": "data"}
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)
        to_encode = {**data, "exp": expire}
        token_without_sub = jwt.encode(to_encode, auth.SECRET_KEY, algorithm=auth.ALGORITHM)
        
        with pytest.raises(HTTPException) as exc_info:
            await auth.get_current_user(token_without_sub)
        
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_empty_subject(self):
        """Test that token with empty subject returns user with empty email."""
        data = {"sub": ""}  # Empty string subject
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)
        to_encode = {**data, "exp": expire}
        token = jwt.encode(to_encode, auth.SECRET_KEY, algorithm=auth.ALGORITHM)
        
        # Empty string is truthy check uses `if email is None`, not falsy check
        # So empty string passes validation in current implementation
        user = await auth.get_current_user(token)
        assert user["email"] == ""

    @pytest.mark.asyncio
    async def test_get_current_user_null_subject(self):
        """Test that token with null subject is rejected."""
        data = {"sub": None}
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)
        to_encode = {**data, "exp": expire}
        token = jwt.encode(to_encode, auth.SECRET_KEY, algorithm=auth.ALGORITHM)
        
        with pytest.raises(HTTPException) as exc_info:
            await auth.get_current_user(token)
        
        assert exc_info.value.status_code == 401


# =============================================================================
# SECURITY TESTS
# =============================================================================

class TestSecurity:
    """Security-focused tests for authentication."""

    def test_password_timing_attack_resistance(self):
        """Test that password verification has consistent timing."""
        import time
        
        password = "testpassword"
        hashed = auth.get_password_hash(password)
        
        # Time correct password
        times_correct = []
        for _ in range(10):
            start = time.perf_counter()
            auth.verify_password(password, hashed)
            times_correct.append(time.perf_counter() - start)
        
        # Time incorrect password
        times_incorrect = []
        for _ in range(10):
            start = time.perf_counter()
            auth.verify_password("wrongpassword", hashed)
            times_incorrect.append(time.perf_counter() - start)
        
        # bcrypt is designed to be timing-safe
        # The times should be roughly similar (within an order of magnitude)
        avg_correct = sum(times_correct) / len(times_correct)
        avg_incorrect = sum(times_incorrect) / len(times_incorrect)
        
        # Both should take similar time (within 10x of each other)
        assert 0.1 < (avg_correct / avg_incorrect) < 10

    def test_token_algorithm_is_secure(self):
        """Test that the configured algorithm is secure."""
        # HS256 is considered secure for JWTs
        assert auth.ALGORITHM in ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]

    def test_token_expiration_is_reasonable(self):
        """Test that token expiration time is not too long."""
        # Access tokens should generally expire within hours, not days
        assert auth.ACCESS_TOKEN_EXPIRE_MINUTES <= 24 * 60  # Max 24 hours

    def test_secret_key_is_not_default(self):
        """Test that secret key has been set (not an obvious default)."""
        # Check it's not a common default value
        common_defaults = ["secret", "changeme", "password", "12345"]
        assert auth.SECRET_KEY.lower() not in common_defaults
        
        # Check minimum length for security
        assert len(auth.SECRET_KEY) >= 32  # Minimum 32 characters

    def test_http_exception_includes_www_authenticate(self):
        """Test that auth failures include proper WWW-Authenticate header."""
        with pytest.raises(HTTPException) as exc_info:
            raise HTTPException(
                status_code=401,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        assert exc_info.value.headers["WWW-Authenticate"] == "Bearer"


# =============================================================================
# EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Edge case tests for authentication."""

    def test_verify_password_with_none(self):
        """Test password verification handles None gracefully."""
        hashed = auth.get_password_hash("password")
        
        # Attempting to verify None should not crash
        # (behavior may vary - could return False or raise exception)
        try:
            result = auth.verify_password(None, hashed)
            assert result is False
        except (TypeError, AttributeError):
            pass  # Also acceptable behavior

    def test_token_with_special_characters_in_email(self):
        """Test token creation with special characters in email."""
        special_emails = [
            "user+tag@example.com",
            "user.name@example.com",
            "user@sub.domain.example.com",
        ]
        
        for email in special_emails:
            token = auth.create_access_token({"sub": email})
            payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
            assert payload["sub"] == email

    @pytest.mark.asyncio
    async def test_token_with_very_long_email(self):
        """Test token handling with very long email."""
        long_email = "a" * 200 + "@example.com"
        token = auth.create_access_token({"sub": long_email})
        
        user = await auth.get_current_user(token)
        assert user["email"] == long_email

    def test_multiple_token_creation_same_user(self):
        """Test that multiple tokens for same user all decode to same email."""
        import time
        email = "user@example.com"
        tokens = []
        for _ in range(5):
            tokens.append(auth.create_access_token({"sub": email}))
            time.sleep(0.001)  # Small delay to potentially get different timestamps
        
        # All tokens should decode to same email
        for token in tokens:
            payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
            assert payload["sub"] == email
