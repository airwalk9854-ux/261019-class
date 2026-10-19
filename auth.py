import hashlib
import hmac
import secrets

def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 600_000).hex()
    return f'pbkdf2_sha256${salt}${digest}'

def verify_password(password, encoded):
    try:
        kind, salt, digest = encoded.split('$')
        return kind == 'pbkdf2_sha256' and hmac.compare_digest(hash_password(password, salt), encoded)
    except (ValueError, TypeError):
        return False

if __name__ == '__main__':
    from getpass import getpass
    print(hash_password(getpass('학생 또는 교사 비밀번호: ')))
