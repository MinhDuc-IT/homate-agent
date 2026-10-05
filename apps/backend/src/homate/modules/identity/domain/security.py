import hashlib
import hmac
import secrets

def hash_pin(pin: str, *, salt_hex: str | None=None) -> str:
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', pin.encode('utf-8'), salt, 120000)
    return f'pbkdf2${salt.hex()}${digest.hex()}'

def verify_pin(stored: str, pin: str) -> bool:
    parts = stored.split('$')
    if len(parts) != 3 or parts[0] != 'pbkdf2':
        return False
    candidate = hash_pin(pin, salt_hex=parts[1])
    return hmac.compare_digest(candidate, stored)
