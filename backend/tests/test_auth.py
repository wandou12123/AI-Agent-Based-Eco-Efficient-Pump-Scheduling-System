"""安全与 JWT 单元测试"""
from app.core.security import hash_password, verify_password, create_token, decode_token


def test_password_hash_roundtrip():
    hashed = hash_password("test-pass-123")
    assert verify_password("test-pass-123", hashed)
    assert not verify_password("wrong", hashed)


def test_jwt_encode_decode():
    token = create_token(1, "testuser", "operator")
    payload = decode_token(token)
    assert payload["sub"] == "1"
    assert payload["username"] == "testuser"
    assert payload["role"] == "operator"
